# -*- coding: utf-8 -*-
"""Shared constants used across multiple route modules."""

ANALYZABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".kt",
    ".html", ".css", ".scss", ".vue", ".svelte",
}

CONFIG_FILES = {
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml", "setup.py",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Gemfile",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    ".github", "Makefile", "tsconfig.json", "angular.json", "next.config.js",
    "vite.config.ts", "vite.config.js", "webpack.config.js",
}

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rb": "ruby", ".rs": "rust", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp", ".cs": "csharp", ".php": "php",
    ".swift": "swift", ".kt": "kotlin", ".html": "html", ".css": "css",
    ".scss": "scss", ".vue": "vue", ".svelte": "svelte",
}

SKIP_DIRS = {"node_modules", "vendor", "__pycache__", ".git", "dist", "build"}

MAX_FILE_SIZE = 100_000
MAX_FILES_TO_ANALYZE = 80
