"""
File Packer Utility for BlitzDev
Handles ZIP creation, validation, and submission packaging
"""

import os
import io
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
from dataclasses import dataclass
import json
import time


@dataclass
class PackResult:
    """Result of packing operation"""
    success: bool
    zip_path: Optional[Path] = None
    zip_bytes: Optional[bytes] = None
    size_bytes: int = 0
    file_count: int = 0
    checksum: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class Packer:
    """Handles file packaging and ZIP operations"""
    
    def __init__(self, max_size_mb: int = 10):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = {'.html', '.css', '.js', '.json', '.md', '.txt'}
        self.excluded_patterns = ['__pycache__', '.git', '.env', 'node_modules']
    
    def create_zip_from_files(
        self,
        files: Dict[str, Union[str, bytes]],
        output_path: Optional[Path] = None,
        metadata: Optional[Dict] = None
    ) -> PackResult:
        """
        Create ZIP from dictionary of filename -> content
        
        Args:
            files: Dictionary mapping filenames to content (str or bytes)
            output_path: Optional path to save ZIP file
            metadata: Optional metadata to include in ZIP
        
        Returns:
            PackResult with ZIP data and metadata
        """
        try:
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(
                zip_buffer,
                'w',
                zipfile.ZIP_DEFLATED,
                compresslevel=6
            ) as zf:
                # Add files
                for filename, content in files.items():
                    if isinstance(content, str):
                        zf.writestr(filename, content)
                    else:
                        zf.writestr(filename, content)
                
                # Add metadata
                if metadata:
                    meta_content = json.dumps(metadata, indent=2, default=str)
                    zf.writestr('blitzdev-meta.json', meta_content)
                
                # Add manifest
                manifest = {
                    "generated_by": "BlitzDev",
                    "timestamp": time.time(),
                    "files": list(files.keys())
                }
                zf.writestr('manifest.json', json.dumps(manifest, indent=2))
            
            zip_bytes = zip_buffer.getvalue()
            
            # Check size
            if len(zip_bytes) > self.max_size_bytes:
                return PackResult(
                    success=False,
                    error=f"ZIP size ({len(zip_bytes)} bytes) exceeds maximum ({self.max_size_bytes} bytes)"
                )
            
            # Calculate checksum
            checksum = hashlib.sha256(zip_bytes).hexdigest()
            
            # Save to file if path provided
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(zip_bytes)
            
            return PackResult(
                success=True,
                zip_path=output_path,
                zip_bytes=zip_bytes,
                size_bytes=len(zip_bytes),
                file_count=len(files),
                checksum=checksum,
                metadata=metadata
            )
            
        except Exception as e:
            return PackResult(success=False, error=str(e))
    
    def create_zip_from_directory(
        self,
        source_dir: Path,
        output_path: Path,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> PackResult:
        """
        Create ZIP from directory contents
        
        Args:
            source_dir: Source directory to pack
            output_path: Output ZIP file path
            include_patterns: Optional glob patterns to include
            exclude_patterns: Optional patterns to exclude
        
        Returns:
            PackResult with ZIP data
        """
        try:
            exclude = self.excluded_patterns + (exclude_patterns or [])
            files_dict = {}
            
            for root, dirs, files in os.walk(source_dir):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in exclude]
                
                for file in files:
                    # Check exclusions
                    if any(pattern in file for pattern in exclude):
                        continue
                    
                    # Check inclusions
                    if include_patterns:
                        if not any(
                            file.endswith(pat.replace('*', '')) 
                            for pat in include_patterns
                        ):
                            continue
                    
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(source_dir)
                    
                    try:
                        with open(file_path, 'rb') as f:
                            files_dict[str(rel_path)] = f.read()
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
            
            return self.create_zip_from_files(files_dict, output_path)
            
        except Exception as e:
            return PackResult(success=False, error=str(e))
    
    def create_webapp_package(
        self,
        html_content: str,
        css_content: Optional[str] = None,
        js_content: Optional[str] = None,
        additional_files: Optional[Dict[str, str]] = None,
        output_path: Optional[Path] = None,
        app_name: str = "blitzdev-app",
        metadata: Optional[Dict] = None
    ) -> PackResult:
        """
        Create a complete web app package
        
        Args:
            html_content: Main HTML content
            css_content: Optional CSS content (embedded or separate)
            js_content: Optional JavaScript content
            additional_files: Additional files to include
            output_path: Output ZIP path
            app_name: Application name
            metadata: Package metadata
        
        Returns:
            PackResult with ZIP data
        """
        files = {
            'index.html': html_content
        }
        
        if css_content:
            files['styles.css'] = css_content
        
        if js_content:
            files['app.js'] = js_content
        
        if additional_files:
            files.update(additional_files)
        
        package_metadata = {
            "app_name": app_name,
            "type": "web_application",
            "framework": "tailwind_css",
            **(metadata or {})
        }
        
        return self.create_zip_from_files(files, output_path, package_metadata)
    
    def validate_zip(self, zip_path: Path) -> PackResult:
        """Validate a ZIP file"""
        try:
            if not zip_path.exists():
                return PackResult(success=False, error="ZIP file not found")
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check for corruption
                bad_file = zf.testzip()
                if bad_file:
                    return PackResult(
                        success=False,
                        error=f"Corrupt file in ZIP: {bad_file}"
                    )
                
                file_list = zf.namelist()
                
                # Check for required files
                if 'index.html' not in file_list:
                    return PackResult(
                        success=False,
                        error="Missing index.html"
                    )
                
                # Get metadata if present
                metadata = None
                if 'blitzdev-meta.json' in file_list:
                    metadata = json.loads(zf.read('blitzdev-meta.json'))
                
                return PackResult(
                    success=True,
                    zip_path=zip_path,
                    size_bytes=zip_path.stat().st_size,
                    file_count=len(file_list),
                    checksum=hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                    metadata=metadata
                )
                
        except zipfile.BadZipFile:
            return PackResult(success=False, error="Invalid ZIP file")
        except Exception as e:
            return PackResult(success=False, error=str(e))
    
    def extract_zip(
        self,
        zip_path: Path,
        extract_dir: Path,
        overwrite: bool = False
    ) -> bool:
        """Extract ZIP to directory"""
        try:
            if extract_dir.exists() and not overwrite:
                return False
            
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            return True
            
        except Exception as e:
            print(f"Extraction error: {e}")
            return False
    
    def get_zip_info(self, zip_path: Path) -> Optional[Dict]:
        """Get detailed ZIP information"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                info = {
                    "files": [],
                    "total_size": 0,
                    "compressed_size": 0
                }
                
                for item in zf.infolist():
                    info["files"].append({
                        "name": item.filename,
                        "size": item.file_size,
                        "compressed": item.compress_size,
                        "date": f"{item.date_time}"
                    })
                    info["total_size"] += item.file_size
                    info["compressed_size"] += item.compress_size
                
                info["compression_ratio"] = (
                    1 - info["compressed_size"] / info["total_size"]
                    if info["total_size"] > 0 else 0
                )
                
                return info
                
        except Exception as e:
            print(f"Error getting ZIP info: {e}")
            return None


# Singleton instance
_packer: Optional[Packer] = None


def get_packer(max_size_mb: int = 10) -> Packer:
    """Get or create packer singleton"""
    global _packer
    if _packer is None:
        _packer = Packer(max_size_mb)
    return _packer
