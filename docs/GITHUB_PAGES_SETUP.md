# GitHub Pages Setup Instructions

This document explains how to enable GitHub Pages for the Orby Web Agent documentation site.

## Setup Steps

### 1. Push the docs folder to GitHub

First, make sure all files in the `docs/` directory are committed and pushed to your GitHub repository:

```bash
git add docs/
git commit -m "Add GitHub Pages documentation site"
git push origin main
```

### 2. Enable GitHub Pages

1. Go to your GitHub repository: `https://github.com/orby-ai-engineering/warc-bench`
2. Click on **Settings** (top navigation)
3. In the left sidebar, click **Pages**
4. Under "Build and deployment":
   - **Source**: Select "Deploy from a branch"
   - **Branch**: Select `main` (or your default branch)
   - **Folder**: Select `/docs`
5. Click **Save**

### 3. Wait for deployment

GitHub will automatically build and deploy your site. This typically takes 1-2 minutes. You'll see a notification at the top of the Pages settings when it's ready.

Your site will be available at:
```
https://orby-ai-engineering.github.io/warc-bench/
```

### 4. Verify the deployment

Once deployed, click the "Visit site" button in the GitHub Pages settings, or navigate directly to the URL above.

## Files Structure

The GitHub Pages site consists of:

```
docs/
├── index.html           # Main documentation page
├── style.css           # Styling for the site
├── _config.yml         # Jekyll configuration (minimal)
├── .nojekyll          # Tells GitHub to skip Jekyll processing
└── GITHUB_PAGES_SETUP.md  # This file
```

## Customization

### Updating the site

To update the documentation:

1. Edit `docs/index.html` or `docs/style.css`
2. Commit and push changes:
   ```bash
   git add docs/
   git commit -m "Update documentation"
   git push origin main
   ```
3. GitHub Pages will automatically rebuild and deploy (takes 1-2 minutes)

### Changing the URL

If you want to use a custom domain:

1. Add a `CNAME` file in the `docs/` directory with your domain:
   ```bash
   echo "your-domain.com" > docs/CNAME
   ```
2. Configure DNS settings with your domain provider
3. Enable "Enforce HTTPS" in GitHub Pages settings

## Troubleshooting

### Site not appearing

- Check that GitHub Pages is enabled in repository settings
- Verify the branch and folder settings are correct
- Check the "Actions" tab for any build errors
- Ensure all files are committed and pushed

### Styling not loading

- Check browser console for any errors
- Verify `style.css` is in the `docs/` directory
- Clear browser cache and reload

### Updates not showing

- Wait 1-2 minutes after pushing changes
- Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
- Check GitHub Actions to ensure deployment completed

## Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Custom Domain Configuration](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
