import os
import re

# Specific replacements for common icons
replacements = {
    "ðŸ’³": "💳", "ðŸ”’": "🔒", "ðŸš€": "🚀", "âž¡ï¸": "➡️", "âž¡": "➡️",
    "ðŸ’¬": "💬", "ðŸŽ“": "🎓", "ðŸ“¥": "📥", "ðŸŒ": "🌍", "ðŸ”“": "🔐",
    "ðŸ‘‘": "👑", "ðŸ“": "📁", "âœ¨": "✨", "âœ…": "✅", "âŒ": "❌",
    "â€”": "—", "â€“": "–", "â†’": "→", "â†“": "↓",
    "ðŸ—„ï¸": "🗄️", "ðŸ—„": "🗄️"
}

count = 0
for root, dirs, files in os.walk("."):
    if any(p in root for p in [".venv", ".git", "__pycache__", "backups"]):
        continue
    for file in files:
        if file.endswith((".py", ".toml", ".md", ".txt", ".json")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="latin-1") as f:
                    content = f.read()
                
                modified = False
                
                # Apply explicit replacements first
                for bad, good in replacements.items():
                    if bad in content:
                        content = content.replace(bad, good)
                        modified = True
                
                # Fallback: Catch remaining leftover mojibake patterns starting with ðŸ or â
                # and safely clean them if they look corrupted
                if "ðŸ" in content or "â" in content:
                    # Optional: clean specific leftover sequences if needed
                    pass

                if modified:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Successfully cleaned: {path}")
                    count += 1
            except Exception as e:
                print(f"Skipped {path}: {e}")

print(f"Done! Total files cleaned: {count}")