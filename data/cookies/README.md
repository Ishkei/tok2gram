# TikTok Cookies Directory

This directory stores TikTok authentication cookies used by the application to access TikTok's API without rate limiting.

## Files

- `tiktok.txt` - Netscape format cookie file for TikTok authentication
- `README.md` - This file

## Security

**IMPORTANT:** Never commit your actual cookies to version control. The `cookies/` directory is gitignored for this reason.

## Setting Up Cookies

1. Log into TikTok in your browser
2. Open Developer Tools (F12) → Application/Storage → Cookies → https://www.tiktok.com
3. Copy the following cookie values:
   - `tt_webid`
   - `tt_webid_v2`
   - `sid_tt`
   - `sessionid`
   - `__ac_nonce`
   - `__ac_signature`
4. Edit `tiktok.txt` and replace the placeholder values with your actual cookies

## Troubleshooting

If you get authentication errors:
- Ensure all required cookies are present
- Try logging out and back into TikTok, then export fresh cookies
- Cookies may expire; export new ones periodically
