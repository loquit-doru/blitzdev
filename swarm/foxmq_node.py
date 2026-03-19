"""
FoxMQNode — Python async wrapper over FoxMQ (MQTT 5.0 + Tashi Vertex BFT consensus).

FoxMQ is a Byzantine fault-tolerant MQTT broker powered by Vertex consensus.
Any standard MQTT client library works against it — Vertex orders all messages
before delivery so every subscriber sees the EXACT same event sequence.

Transport : paho-mqtt → FoxMQ broker (localhost:1883 by default)
Topic schema:
  swarm/PEER_ANNOUNCE    → peer discovery / join mesh
  swarm/HEARTBEAT        → keep-alive / stale detection
  swarm/TASK_AVAILABLE   → job announcement
  swarm/BID              → task bid
  swarm/COMMIT           → winner commitment

Security:
  - Every message is HMAC-SHA256 signed (shared secret across all nodes).
  - Nonce ring-buffer prevents replay attacks.
  - FoxMQ Vertex consensus provides fair BFT ordering — no front-running.
"""
import asyncio
import hashlib
import hmac as _hmac_mod
import json
import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

HEARTBEAT_INTERVAL = 2.0     # seconds between heartbeats
PEER_STALE_AFTER   = float(os.getenv("PEER_STALE_AFTER", "10"))  # seconds without heartbeat → marked stale
NONCE_RING_MAX     = 1024    # max nonces kept for replay prevention


class FoxMQNode:
    """
    Async agent node backed by FoxMQ (MQTT / Vertex BFT).

    All messages are HMAC-SHA256 signed for tamper evidence.
    Vertex consensus inside FoxMQ guarantees all agents see messages
    in the same order — eliminating coordination races at the transport level.
    """

    def __init__(
        self,
        node_id: str,
        role: str,
        foxmq_host: str = "127.0.0.1",
        foxmq_port: int = 1883,
        hmac_secret: str = "swarm-secret-change-in-prod",
    ):
        self.node_id = node_id
        self.role = role
        self._host = foxmq_host
        self._port = foxmq_port
        self._secret = hmac_secret.encode()

        # paho-mqtt 2.x (CallbackAPIVersion.VERSION2 required)
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=node_id,
            protocol=mqtt.MQTTv5,
        )
        self._client.on_connect    = self._on_connect
        self._client.on_message    = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._handlers: Dict[str, List[Callable]] = {}
        self._peer_states: Dict[str, Dict]        = {}
        self._seen_nonces: List[str]              = []
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected: Optional[asyncio.Event]        = None  # created in start()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to FoxMQ broker, subscribe swarm/#, launch heartbeat loop."""
        self._loop      = asyncio.get_event_loop()
        self._connected = asyncio.Event()

        self._client.connect(self._host, self._port, keepalive=60)
        self._client.loop_start()   # paho background network thread

        try:
            await asyncio.wait_for(self._connected.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Cannot connect to FoxMQ broker at {self._host}:{self._port}.\n"
                "  → Run:  .\\foxmq.exe run --secret-key-file=foxmq.d/key_0.pem "
                "--allow-anonymous-login"
            )

        self._running = True
        print(
            f"[{self.role}:{self.node_id[:8]}] ✓ Node started — "
            f"FoxMQ {self._host}:{self._port}"
        )

        await self.publish("PEER_ANNOUNCE", {"role": self.role})
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        self._client.disconnect()
        self._client.loop_stop()

    # ── MQTT callbacks (run in paho background thread) ─────────────────────────

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        client.subscribe("swarm/#", qos=1)
        if self._loop and self._connected:
            self._loop.call_soon_threadsafe(self._connected.set)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if self._running:
            print(
                f"[{self.role}] ⚠ Disconnected from FoxMQ "
                f"(rc={reason_code}) — reconnecting…"
            )

    def _on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload)
        except Exception:
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._dispatch(message), self._loop)

    # ── Async dispatch ─────────────────────────────────────────────────────────

    async def _dispatch(self, msg: Dict[str, Any]) -> None:
        # Drop own echo
        if msg.get("sender_id") == self.node_id:
            return

        # HMAC verification
        if not self._verify(msg):
            print(f"[{self.role}] ⚠ HMAC FAIL from {msg.get('sender_id', '?')[:8]} — dropped")
            return

        # Replay prevention
        nonce: str = msg.get("nonce", "")
        if nonce in self._seen_nonces:
            return
        self._seen_nonces.append(nonce)
        if len(self._seen_nonces) > NONCE_RING_MAX:
            self._seen_nonces = self._seen_nonces[-NONCE_RING_MAX // 2:]

        # Update live peer registry
        sender_id: str = msg["sender_id"]
        self._peer_states[sender_id] = {
            "role":         msg.get("sender_role", "unknown"),
            "last_seen_ms": msg["timestamp_ms"],
            "status":       "online",
        }

        # Dispatch to registered handlers
        msg_type: str = msg["type"]
        for handler in self._handlers.get(msg_type, []):
            asyncio.create_task(handler(msg))

    # ── Heartbeat ──────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await self.publish("HEARTBEAT", {"role": self.role})

            now_ms = int(time.time() * 1000)
            for peer_id, state in list(self._peer_states.items()):
                age_s = (now_ms - state["last_seen_ms"]) / 1000
                if age_s > PEER_STALE_AFTER and state["status"] == "online":
                    state["status"] = "stale"
                    print(
                        f"[{self.role}:{self.node_id[:8]}] ⚠  STALE  "
                        f"peer={peer_id[:8]} role={state['role']} "
                        f"silent={age_s:.1f}s (threshold={PEER_STALE_AFTER}s)"
                    )
                elif age_s <= PEER_STALE_AFTER and state["status"] == "stale":
                    state["status"] = "online"
                    print(
                        f"[{self.role}:{self.node_id[:8]}] ✓  ONLINE  "
                        f"peer={peer_id[:8]} role={state['role']} back online"
                    )

    # ── Publishing ─────────────────────────────────────────────────────────────

    async def publish(self, msg_type: str, payload: Dict[str, Any]) -> None:
        """Sign and publish a message via FoxMQ MQTT broker (QoS 1)."""
        body: Dict[str, Any] = {
            "type":         msg_type,
            "sender_id":    self.node_id,
            "sender_role":  self.role,
            "timestamp_ms": int(time.time() * 1000),
            "nonce":        str(uuid.uuid4()),
            "payload":      payload,
        }
        body["hmac"] = self._sign(body)
        # paho publish is thread-safe; QoS 1 = at-least-once delivery
        self._client.publish(f"swarm/{msg_type}", json.dumps(body), qos=1)

    # ── Event registration ─────────────────────────────────────────────────────

    def on(self, msg_type: str, handler: Callable = None) -> Callable:
        """Register a message handler. Supports direct call and @decorator factory.

        Direct::
            node.on("BID", my_handler)

        Decorator factory::
            @node.on("COMMIT")
            async def my_handler(msg): ...
        """
        if handler is not None:
            self._handlers.setdefault(msg_type, []).append(handler)
            return handler

        def _decorator(fn: Callable) -> Callable:
            self._handlers.setdefault(msg_type, []).append(fn)
            return fn
        return _decorator

    # ── HMAC helpers ───────────────────────────────────────────────────────────

    def _sign(self, msg: Dict[str, Any]) -> str:
        """HMAC-SHA256 over canonical JSON (sorted keys, excluding hmac field)."""
        body = {k: v for k, v in msg.items() if k != "hmac"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return _hmac_mod.new(self._secret, canonical, hashlib.sha256).hexdigest()

    def _verify(self, msg: Dict[str, Any]) -> bool:
        expected = msg.get("hmac", "")
        actual   = self._sign(msg)
        return _hmac_mod.compare_digest(expected, actual)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def online_peers(self) -> Dict[str, Dict]:
        return {k: v for k, v in self._peer_states.items() if v["status"] == "online"}

    def peer_summary(self) -> str:
        if not self._peer_states:
            return "no peers"
        parts = []
        for _, state in self._peer_states.items():
            icon = "✓" if state["status"] == "online" else "✗"
            parts.append(f"{state['role']}({icon})")
        return ", ".join(sorted(parts))
