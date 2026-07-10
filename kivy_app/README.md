# 洇洇专用 — Android APK

## Build with GitHub Actions (easiest — no local tools needed)

1. Push this repo to GitHub:
   ```bash
   cd F:\中文学习系统\ChineseLearningAssistant
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YinYinApp.git
   git push -u origin main
   ```

2. Go to your repo on GitHub → **Actions** tab → "Build APK" workflow
3. Click **Run workflow** → wait ~40 min
4. Download the APK from the workflow run's **Artifacts** section
5. Install on any Android phone (Settings → Security → Install from unknown sources)

## Manual build (requires Linux / WSL)

```bash
cd kivy_app
pip install buildozer cython
buildozer android debug
# APK at: kivy_app/bin/YinYinApp-1.0.0-arm64-v8a-debug.apk
```
