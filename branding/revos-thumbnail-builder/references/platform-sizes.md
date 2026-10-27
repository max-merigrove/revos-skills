# Platform sizes

Sizes the renderer knows (`sizes` in the spec). The first size listed in a spec is the one compared side by side. Platforms change their specifications; check the current help page before a launch.

| Size name | Pixels | Use | Notes |
|---|---|---|---|
| `youtube` | 1280x720 | YouTube video thumbnail | YouTube asks for 1280x720 (minimum width 640) as JPG, PNG or GIF under 2 MB. The script writes a JPEG twin if the PNG is over 2 MB. The duration badge covers the bottom right |
| `widescreen` | 1920x1080 | LinkedIn native video, Vimeo, course platforms, webinar replays | Same layout as `youtube` at a higher resolution |
| `square` | 1080x1080 | Podcast episode art, LinkedIn and X feed posts for a clip | Words on top, picture below |
| `vertical` | 1080x1920 | Shorts, Reels and TikTok covers | Words sit in the upper middle: the caption and buttons cover the bottom and the right, and an Instagram profile grid shows a centre 3:4 crop |
| `podcast` | 3000x3000 | Podcast show art | Apple Podcasts asks for square art between 1400 and 3000 px |

Shorts covers are chosen from a frame of the video on most surfaces, so a vertical cover matters most on Reels and TikTok, where a cover image can be set.

The readability test widths per shape: 16:9 at 360, 246 and 168 px; square at 300, 160 and 110 px; vertical at 270, 180 and 120 px. These are approximate sizes seen in feeds, chosen from looking at the platforms, not published figures.
