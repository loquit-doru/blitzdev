"""
Template & Component Library for BlitzDev
Pre-built HTML templates, reusable components, CDN bundles, and SVG icons.
Reduces LLM token waste on boilerplate → more budget for unique logic → better scores.
"""

from typing import Dict, Any, List, Optional

# ─────────────────────────────────────────────────────────────
# CDN BUNDLES — per-app-type external libraries
# ─────────────────────────────────────────────────────────────
CDN_BUNDLES: Dict[str, List[str]] = {
    "charts": [
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>',
    ],
    "syntax_highlight": [
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css">',
        '<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>',
    ],
    "markdown": [
        '<script src="https://cdn.jsdelivr.net/npm/marked@12.0.0/marked.min.js"></script>',
    ],
    "sortable": [
        '<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>',
    ],
    "confetti": [
        '<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js"></script>',
    ],
    "anime": [
        '<script src="https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js"></script>',
    ],
}

# Map app_type → which CDN bundles to include
APP_TYPE_CDNS: Dict[str, List[str]] = {
    "dashboard":           ["charts"],
    "data_visualization":  ["charts"],
    "code_showcase":       ["syntax_highlight"],
    "tutorial":            ["syntax_highlight"],
    "article":             ["charts"],
    "game":                ["confetti"],
    "creative":            ["anime", "confetti"],
}

# ─────────────────────────────────────────────────────────────
# SVG_ICONS — inline hero-style icons (24×24 viewBox)
# ─────────────────────────────────────────────────────────────
SVG_ICONS: Dict[str, str] = {
    "home": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955a1.126 1.126 0 0 1 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"/></svg>',
    "sun": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"/></svg>',
    "moon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75 9.75 9.75 0 0 1 8.25 6c0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 15.75 9.75 9.75 0 0 0 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z"/></svg>',
    "menu": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"/></svg>',
    "close": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></svg>',
    "arrow_right": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"/></svg>',
    "arrow_left": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"/></svg>',
    "star": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"/></svg>',
    "heart": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z"/></svg>',
    "chart_bar": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"/></svg>',
    "code": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"/></svg>',
    "document": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"/></svg>',
    "clipboard": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3a2.25 2.25 0 0 0-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"/></svg>',
    "cog": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/></svg>',
    "play": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"/></svg>',
    "download": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"/></svg>',
    "share": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z"/></svg>',
    "sparkles": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/></svg>',
    "trophy": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 0 1 3 3h-15a3 3 0 0 1 3-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 0 1-.982-3.172M9.497 14.25a7.454 7.454 0 0 0 .981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 0 0 7.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M18.75 4.236c.982.143 1.954.317 2.916.52A6.003 6.003 0 0 1 16.27 9.728M18.75 4.236V4.5c0 2.108-.966 3.99-2.48 5.228m0 0a6.003 6.003 0 0 1-2.77.83m-6 0a6.003 6.003 0 0 1-2.77-.83"/></svg>',
    "bolt": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"/></svg>',
    "fire": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0 1 12 21 8.25 8.25 0 0 1 6.038 7.047 8.287 8.287 0 0 0 9 9.601a8.983 8.983 0 0 1 3.361-6.867 8.21 8.21 0 0 0 3 2.48Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 0 0 .495-7.468 5.99 5.99 0 0 0-1.925 3.547 5.975 5.975 0 0 1-2.133-1.001A3.75 3.75 0 0 0 12 18Z"/></svg>',
    "trash": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"/></svg>',
    "edit": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/></svg>',
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>',
    "mail": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/></svg>',
    "bell": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"/></svg>',
    "calendar": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>',
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"/></svg>',
    "arrow_up": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18"/></svg>',
    "arrow_down": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3"/></svg>',
}


# ─────────────────────────────────────────────────────────────
# COMPONENT LIBRARY — reusable HTML snippets injected into prompt
# ─────────────────────────────────────────────────────────────
COMPONENTS: Dict[str, str] = {

    "responsive_nav": """<!-- Responsive Navigation (copy & customize) -->
<nav class="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <span class="text-xl font-bold text-primary">AppName</span>
      </div>
      <div class="hidden md:flex items-center space-x-8">
        <a href="#" class="text-gray-700 hover:text-primary transition-colors">Home</a>
        <a href="#" class="text-gray-700 hover:text-primary transition-colors">Features</a>
        <a href="#" class="text-gray-700 hover:text-primary transition-colors">About</a>
        <button class="bg-primary text-white px-4 py-2 rounded-lg hover:opacity-90 transition-all">CTA</button>
      </div>
      <button id="mobileMenuBtn" class="md:hidden flex items-center" aria-label="Menu">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </div>
  <div id="mobileMenu" class="hidden md:hidden px-4 pb-4 space-y-2">
    <a href="#" class="block py-2 text-gray-700">Home</a>
    <a href="#" class="block py-2 text-gray-700">Features</a>
    <a href="#" class="block py-2 text-gray-700">About</a>
  </div>
</nav>
<script>
document.getElementById('mobileMenuBtn')?.addEventListener('click', () => {
  document.getElementById('mobileMenu')?.classList.toggle('hidden');
});
</script>""",

    "dark_mode_toggle": """<!-- Dark Mode Toggle (add to nav) -->
<button id="darkToggle" class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Toggle dark mode">
  <svg id="sunIcon" class="w-5 h-5 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"/></svg>
  <svg id="moonIcon" class="w-5 h-5 block dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21.752 15.002A9.72 9.72 0 0118 15.75 9.75 9.75 0 018.25 6c0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 15.75 9.75 9.75 0 0012.75 21a9.753 9.753 0 009.002-5.998Z"/></svg>
</button>
<script>
document.getElementById('darkToggle')?.addEventListener('click', () => {
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
});
if (localStorage.getItem('theme') === 'dark') document.documentElement.classList.add('dark');
</script>""",

    "hero_section": """<!-- Hero Section -->
<section class="relative overflow-hidden py-20 sm:py-32">
  <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5"></div>
  <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-gray-900 mb-6">
      Headline Goes Here
    </h1>
    <p class="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10">
      A compelling sub-headline that explains the value proposition.
    </p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <button class="bg-primary text-white px-8 py-3 rounded-xl text-lg font-semibold hover:opacity-90 transition-all hover:scale-105 shadow-lg shadow-primary/25">
        Get Started
      </button>
      <button class="border-2 border-gray-300 text-gray-700 px-8 py-3 rounded-xl text-lg font-semibold hover:border-primary hover:text-primary transition-all">
        Learn More
      </button>
    </div>
  </div>
</section>""",

    "stat_cards": """<!-- Stat Cards Row -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
    <div class="flex items-center justify-between mb-4">
      <span class="text-sm font-medium text-gray-500">Total Users</span>
      <span class="bg-green-100 text-green-700 text-xs font-bold px-2 py-1 rounded-full">+12%</span>
    </div>
    <div class="text-3xl font-bold text-gray-900">24,521</div>
    <div class="mt-2 text-sm text-gray-400">vs last month</div>
  </div>
  <!-- Repeat for other stats -->
</div>""",

    "card_grid": """<!-- Card Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
  <div class="group bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
    <div class="h-48 bg-gradient-to-br from-primary/20 to-accent/20"></div>
    <div class="p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-2 group-hover:text-primary transition-colors">Card Title</h3>
      <p class="text-gray-600 text-sm mb-4">Card description goes here with a brief summary.</p>
      <a href="#" class="text-primary font-medium text-sm hover:underline">Learn more →</a>
    </div>
  </div>
  <!-- Repeat -->
</div>""",

    "modal": """<!-- Modal Component -->
<div id="modal" class="hidden fixed inset-0 z-50 overflow-y-auto" aria-modal="true" role="dialog">
  <div class="flex items-center justify-center min-h-screen p-4">
    <div id="modalBackdrop" class="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"></div>
    <div class="relative bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 transform transition-all">
      <button id="modalClose" class="absolute top-4 right-4 text-gray-400 hover:text-gray-600" aria-label="Close">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
      <h3 class="text-xl font-bold mb-4">Modal Title</h3>
      <p class="text-gray-600 mb-6">Modal content goes here.</p>
      <div class="flex justify-end gap-3">
        <button class="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">Cancel</button>
        <button class="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-all">Confirm</button>
      </div>
    </div>
  </div>
</div>
<script>
function openModal() { document.getElementById('modal')?.classList.remove('hidden'); }
function closeModal() { document.getElementById('modal')?.classList.add('hidden'); }
document.getElementById('modalClose')?.addEventListener('click', closeModal);
document.getElementById('modalBackdrop')?.addEventListener('click', closeModal);
</script>""",

    "toast_notification": """<!-- Toast Notification System -->
<div id="toastContainer" class="fixed bottom-4 right-4 z-50 flex flex-col gap-2"></div>
<script>
function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const colors = { success: 'bg-green-500', error: 'bg-red-500', info: 'bg-blue-500', warning: 'bg-yellow-500 text-black' };
  const toast = document.createElement('div');
  toast.className = `${colors[type] || colors.info} text-white px-6 py-3 rounded-xl shadow-lg transform translate-x-full transition-transform duration-300 flex items-center gap-2`;
  toast.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()" class="ml-2 hover:opacity-70">&times;</button>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.remove('translate-x-full'));
  setTimeout(() => { toast.classList.add('translate-x-full'); setTimeout(() => toast.remove(), 300); }, 3000);
}
</script>""",

    "tabs": """<!-- Tab Navigation -->
<div class="border-b border-gray-200 mb-6">
  <nav class="flex gap-8" role="tablist">
    <button class="tab-btn py-3 text-sm font-medium border-b-2 border-primary text-primary" data-tab="tab1" role="tab" aria-selected="true">Tab 1</button>
    <button class="tab-btn py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="tab2" role="tab">Tab 2</button>
    <button class="tab-btn py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="tab3" role="tab">Tab 3</button>
  </nav>
</div>
<div id="tab1" class="tab-panel">Tab 1 content</div>
<div id="tab2" class="tab-panel hidden">Tab 2 content</div>
<div id="tab3" class="tab-panel hidden">Tab 3 content</div>
<script>
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('border-primary', 'text-primary'); b.classList.add('border-transparent', 'text-gray-500'); b.setAttribute('aria-selected', 'false'); });
    btn.classList.add('border-primary', 'text-primary'); btn.classList.remove('border-transparent', 'text-gray-500'); btn.setAttribute('aria-selected', 'true');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(btn.dataset.tab)?.classList.remove('hidden');
  });
});
</script>""",

    "sidebar_layout": """<!-- Sidebar + Content Layout -->
<div class="flex min-h-screen">
  <aside class="hidden lg:flex lg:flex-col w-64 bg-gray-900 text-white">
    <div class="p-6 border-b border-gray-800">
      <span class="text-xl font-bold">AppName</span>
    </div>
    <nav class="flex-1 p-4 space-y-1">
      <a href="#" class="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-800 text-white">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
        Dashboard
      </a>
      <a href="#" class="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-colors">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
        Analytics
      </a>
    </nav>
  </aside>
  <main class="flex-1 bg-gray-50">
    <header class="bg-white border-b border-gray-200 px-6 py-4">
      <h1 class="text-xl font-semibold text-gray-900">Page Title</h1>
    </header>
    <div class="p-6">
      <!-- Main content here -->
    </div>
  </main>
</div>""",

    "footer": """<!-- Footer -->
<footer class="bg-gray-900 text-gray-400 py-12 mt-auto">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
      <div>
        <h3 class="text-white font-semibold mb-4">Product</h3>
        <ul class="space-y-2 text-sm"><li><a href="#" class="hover:text-white transition-colors">Features</a></li><li><a href="#" class="hover:text-white transition-colors">Pricing</a></li></ul>
      </div>
      <div>
        <h3 class="text-white font-semibold mb-4">Company</h3>
        <ul class="space-y-2 text-sm"><li><a href="#" class="hover:text-white transition-colors">About</a></li><li><a href="#" class="hover:text-white transition-colors">Blog</a></li></ul>
      </div>
    </div>
    <div class="border-t border-gray-800 pt-6 text-center text-sm">&copy; 2025 AppName. All rights reserved.</div>
  </div>
</footer>""",

    "copy_button": """<!-- Copy to Clipboard Button -->
<button onclick="copyToClipboard(this)" class="flex items-center gap-1 px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-md transition-colors" aria-label="Copy">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
  Copy
</button>
<script>
function copyToClipboard(btn) {
  const code = btn.closest('.code-block')?.querySelector('code')?.textContent || '';
  navigator.clipboard.writeText(code).then(() => {
    btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Copied!';
    setTimeout(() => { btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg> Copy'; }, 2000);
  });
}
</script>""",

    "progress_bar": """<!-- Animated Progress Bar -->
<div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
  <div id="progressBar" class="bg-gradient-to-r from-primary to-accent h-3 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
</div>
<script>
function setProgress(percent) {
  document.getElementById('progressBar').style.width = Math.min(100, Math.max(0, percent)) + '%';
}
</script>""",

    "search_input": """<!-- Search Input with Icon -->
<div class="relative max-w-md">
  <input type="text" id="searchInput" placeholder="Search..." class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all" aria-label="Search">
  <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
</div>""",

    "loading_spinner": """<!-- Loading Spinner -->
<div id="spinner" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
  <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
</div>
<script>
function showLoading() { document.getElementById('spinner')?.classList.remove('hidden'); }
function hideLoading() { document.getElementById('spinner')?.classList.add('hidden'); }
</script>""",

    "chart_container": """<!-- Chart.js Container (requires Chart.js CDN) -->
<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-gray-900">Chart Title</h3>
    <select id="chartRange" class="text-sm border border-gray-300 rounded-lg px-3 py-1.5">
      <option value="7d">Last 7 days</option>
      <option value="30d">Last 30 days</option>
      <option value="90d">Last 90 days</option>
    </select>
  </div>
  <canvas id="myChart" height="300"></canvas>
</div>""",
}


# ─────────────────────────────────────────────────────────────
# APP TYPE STARTER TEMPLATES — minimal but high-quality skeletons
# These give the LLM a head start so it focuses on unique logic
# ─────────────────────────────────────────────────────────────
APP_TYPE_STARTERS: Dict[str, Dict[str, Any]] = {
    "landing_page": {
        "description": "Landing page with hero, features, CTA, footer",
        "suggested_components": ["responsive_nav", "hero_section", "card_grid", "footer", "dark_mode_toggle"],
        "structure_hint": "header > hero > features grid > testimonials > CTA > footer",
    },
    "dashboard": {
        "description": "Data dashboard with sidebar, stats, charts",
        "suggested_components": ["sidebar_layout", "stat_cards", "chart_container", "tabs", "toast_notification"],
        "structure_hint": "sidebar (nav) + main area (stats row > charts grid > data table)",
        "extra_cdns": ["charts"],
    },
    "portfolio": {
        "description": "Portfolio/personal site with projects gallery",
        "suggested_components": ["responsive_nav", "hero_section", "card_grid", "modal", "footer"],
        "structure_hint": "hero intro > skill tags > projects grid (clickable → modal detail) > contact form > footer",
    },
    "e_commerce": {
        "description": "Product showcase with cart functionality",
        "suggested_components": ["responsive_nav", "search_input", "card_grid", "modal", "toast_notification", "footer"],
        "structure_hint": "nav (search + cart icon) > filters sidebar + product grid > product modal > cart drawer > checkout",
    },
    "game": {
        "description": "Interactive browser game",
        "suggested_components": ["toast_notification", "modal"],
        "structure_hint": "game header (score, level) > canvas/game-area > controls > game-over modal with restart",
        "extra_cdns": ["confetti"],
    },
    "calculator": {
        "description": "Functional calculator tool",
        "suggested_components": ["dark_mode_toggle", "toast_notification"],
        "structure_hint": "centered card > display area > button grid (numbers + operators) > history panel",
    },
    "interactive_app": {
        "description": "Generic interactive web application",
        "suggested_components": ["responsive_nav", "tabs", "modal", "toast_notification", "footer"],
        "structure_hint": "nav > main content with tab sections > action buttons > result display > footer",
    },
    "text_content": {
        "description": "Beautiful typographic presentation of text content",
        "suggested_components": ["dark_mode_toggle", "copy_button"],
        "structure_hint": "elegant header > main text content with proper typography > decorative dividers > share/copy buttons",
    },
    "code_showcase": {
        "description": "Code presentation with syntax highlighting",
        "suggested_components": ["dark_mode_toggle", "tabs", "copy_button"],
        "structure_hint": "header > code block with line numbers + copy + syntax highlight > explanation sections > run button if JS",
        "extra_cdns": ["syntax_highlight"],
    },
    "tutorial": {
        "description": "Step-by-step interactive tutorial",
        "suggested_components": ["responsive_nav", "tabs", "progress_bar", "copy_button"],
        "structure_hint": "sticky sidebar TOC > progress bar > numbered steps with code blocks > mark-complete checkboxes",
        "extra_cdns": ["syntax_highlight"],
    },
    "article": {
        "description": "Data-rich article or analysis presentation",
        "suggested_components": ["responsive_nav", "stat_cards", "chart_container", "tabs", "footer"],
        "structure_hint": "header > executive summary cards > chart visualizations > tabbed sections > conclusion > footer",
        "extra_cdns": ["charts"],
    },
    "data_visualization": {
        "description": "Charts and data visualization dashboard",
        "suggested_components": ["sidebar_layout", "stat_cards", "chart_container", "tabs"],
        "structure_hint": "sidebar filters > stat cards row > multiple chart cards (bar, line, pie) > data table",
        "extra_cdns": ["charts"],
    },
    "utility": {
        "description": "Functional tool/converter/generator",
        "suggested_components": ["dark_mode_toggle", "toast_notification", "loading_spinner"],
        "structure_hint": "header > input area > process button > output/result area > history list > copy/download buttons",
    },
    "creative": {
        "description": "Immersive creative/artistic HTML experience",
        "suggested_components": ["dark_mode_toggle", "modal"],
        "structure_hint": "full-screen immersive layout > animated sections > interactive elements > Easter eggs",
        "extra_cdns": ["anime", "confetti"],
    },
    "documentation": {
        "description": "Documentation site with sidebar navigation",
        "suggested_components": ["sidebar_layout", "search_input", "tabs", "copy_button"],
        "structure_hint": "sidebar sections > search > main content with headings > code examples with copy > prev/next navigation",
        "extra_cdns": ["syntax_highlight"],
    },
    "blog": {
        "description": "Blog post or article layout",
        "suggested_components": ["responsive_nav", "dark_mode_toggle", "footer"],
        "structure_hint": "nav > article header (title, date, tags) > rich content > author bio > related posts > footer",
    },
    "form_wizard": {
        "description": "Multi-step form with validation",
        "suggested_components": ["responsive_nav", "progress_bar", "toast_notification"],
        "structure_hint": "progress steps indicator > form sections (one per step) > prev/next buttons > summary/review > submit",
    },
}


# ─────────────────────────────────────────────────────────────
# CSS UTILITIES — common animations and utility styles
# ─────────────────────────────────────────────────────────────
CSS_UTILITIES = """
/* Smooth entry animations */
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideInRight { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
@keyframes pulse-glow { 0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.3); } 50% { box-shadow: 0 0 20px 5px rgba(59,130,246,0.15); } }
.animate-fade-in-up { animation: fadeInUp 0.6s ease-out forwards; }
.animate-fade-in { animation: fadeIn 0.4s ease-out forwards; }
.animate-slide-in { animation: slideInRight 0.5s ease-out forwards; }
.animate-pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }

/* Staggered children animation */
.stagger > * { opacity: 0; animation: fadeInUp 0.5s ease-out forwards; }
.stagger > *:nth-child(1) { animation-delay: 0.1s; }
.stagger > *:nth-child(2) { animation-delay: 0.2s; }
.stagger > *:nth-child(3) { animation-delay: 0.3s; }
.stagger > *:nth-child(4) { animation-delay: 0.4s; }
.stagger > *:nth-child(5) { animation-delay: 0.5s; }
.stagger > *:nth-child(6) { animation-delay: 0.6s; }

/* Smooth scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Dark mode base */
.dark { color-scheme: dark; }
.dark body { background-color: #0f172a; color: #e2e8f0; }

/* Glass morphism utility */
.glass { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15); }
"""


# ─────────────────────────────────────────────────────────────
# PUBLIC API — used by BuilderAgent
# ─────────────────────────────────────────────────────────────

def get_template_context(app_type: str) -> Dict[str, Any]:
    """
    Get the full template context for a given app type.
    Returns CDN tags, component snippets, structure hints, and CSS utilities.
    
    Args:
        app_type: The AppType value (e.g. "dashboard", "game", "text_content")
    
    Returns:
        Dict with keys: cdn_tags, components, structure_hint, css_utilities, icon_catalog
    """
    starter = APP_TYPE_STARTERS.get(app_type, APP_TYPE_STARTERS.get("interactive_app", {}))
    
    # Collect CDN tags
    cdn_tags: List[str] = []
    extra_cdn_keys = starter.get("extra_cdns", [])
    # Also check the global APP_TYPE_CDNS mapping
    global_cdn_keys = APP_TYPE_CDNS.get(app_type, [])
    all_cdn_keys = list(set(extra_cdn_keys + global_cdn_keys))
    
    for key in all_cdn_keys:
        cdn_tags.extend(CDN_BUNDLES.get(key, []))
    
    # Collect suggested component snippets
    component_snippets: Dict[str, str] = {}
    for comp_name in starter.get("suggested_components", []):
        if comp_name in COMPONENTS:
            component_snippets[comp_name] = COMPONENTS[comp_name]
    
    # Build icon catalog summary (names only, to save tokens)
    icon_names = list(SVG_ICONS.keys())
    
    return {
        "cdn_tags": cdn_tags,
        "components": component_snippets,
        "structure_hint": starter.get("structure_hint", ""),
        "description": starter.get("description", ""),
        "css_utilities": CSS_UTILITIES,
        "available_icons": icon_names,
    }


def format_components_for_prompt(components: Dict[str, str], max_components: int = 4) -> str:
    """
    Format component snippets into a string suitable for injection into the builder prompt.
    Limits to max_components to avoid token bloat.
    
    Args:
        components: Dict of component_name → HTML snippet
        max_components: Maximum number of components to include
    
    Returns:
        Formatted string with component HTML ready for prompt injection
    """
    if not components:
        return ""
    
    parts = []
    for i, (name, html) in enumerate(components.items()):
        if i >= max_components:
            remaining = list(components.keys())[max_components:]
            parts.append(f"\n(Also available but not shown: {', '.join(remaining)})")
            break
        parts.append(f"### {name.upper().replace('_', ' ')}\n{html}")
    
    return "\n\n".join(parts)


def get_icons_for_prompt(icon_names: List[str]) -> str:
    """
    Get specific SVG icons as ready-to-paste HTML.
    
    Args:
        icon_names: List of icon names to include
    
    Returns:
        String with SVG icons ready for the LLM to use
    """
    parts = []
    for name in icon_names:
        if name in SVG_ICONS:
            parts.append(f"<!-- icon: {name} --> {SVG_ICONS[name]}")
    return "\n".join(parts)


def get_all_icon_names() -> List[str]:
    """Return all available icon names."""
    return list(SVG_ICONS.keys())
