# Publishing the WARC-Bench Website

This guide explains how to publish the research website to GitHub Pages.

## Website URL

Once published, the website will be available at:
**https://sanjari-orb.github.io/warc-bench/**

## How to Enable GitHub Pages

1. **Go to your repository on GitHub**:
   https://github.com/sanjari-orb/warc-bench

2. **Navigate to Settings**:
   - Click on "Settings" in the repository menu

3. **Go to Pages section**:
   - In the left sidebar, click on "Pages" (under "Code and automation")

4. **Configure the source**:
   - Under "Build and deployment"
   - Source: Select "Deploy from a branch"
   - Branch: Select "main" and "/docs" folder
   - Click "Save"

5. **Wait for deployment**:
   - GitHub will automatically build and deploy your site
   - This usually takes 1-2 minutes
   - You'll see a green checkmark when it's ready

6. **Visit your site**:
   - Go to https://sanjari-orb.github.io/warc-bench/
   - The website should now be live!

## Updating the Website

Any changes you make to files in the `docs/` folder will automatically be deployed when you push to the main branch:

```bash
# Make changes to docs/index.html or add new files
git add docs/
git commit -m "Update website content"
git push origin main

# Wait 1-2 minutes for GitHub Pages to rebuild
```

## Current Website Structure

```
docs/
├── index.html       # Main website page
├── video1.gif       # Demo video 1 (ZenDesk)
├── video2.gif       # Demo video 2 (GitHub)
├── video3.gif       # Demo video 3 (Synthetic 1)
├── video4.gif       # Demo video 4 (Synthetic 2)
├── _config.yml      # Jekyll configuration
└── .nojekyll        # Disables Jekyll processing
```

## Updating Links

Once the website is live, you can update the placeholder links in the website:

1. **Project Website** - Already set to https://sanjari-orb.github.io/warc-bench/
2. **arXiv Paper** - Already set to https://arxiv.org/abs/2510.09872
3. **GitHub** - Already set to https://github.com/sanjari-orb/warc-bench
4. **Dataset** - Update with your dataset hosting URL (HuggingFace, Google Drive, etc.)

Edit `docs/index.html` and find the links section to update the dataset placeholder.

## Troubleshooting

**Website not showing up?**
- Check that GitHub Pages is enabled in repository settings
- Verify you selected the "main" branch and "/docs" folder
- Wait a few minutes for the initial deployment

**Changes not appearing?**
- Check the Actions tab on GitHub to see if the deployment succeeded
- Clear your browser cache
- Wait 1-2 minutes after pushing changes

**Videos not loading?**
- Check that video files are under 100MB (current videos are ~15MB total)
- Verify video files are in the docs/ directory
- Check browser console for any errors

## Next Steps

After publishing:
1. Test the website at https://sanjari-orb.github.io/warc-bench/
2. Update the dataset link once you host the benchmark data
3. Share the website link in your paper and social media!
