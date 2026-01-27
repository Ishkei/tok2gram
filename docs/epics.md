---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics"]
inputDocuments: ["docs/prd-drafted.md", "docs/architecture-drafted.md"]
---

# TikTok → Telegram Local Monitor & Reposter - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for TikTok → Telegram Local Monitor & Reposter, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Monitor specified TikTok creators for new content  
FR2: Fetch latest 10 posts per creator  
FR3: Sort posts oldest to newest  
FR4: Download unseen posts  
FR5: Upload videos to Telegram with best quality and caption + attribution  
FR6: Upload slideshows as Telegram media groups with caption on first image  
FR7: Handle mixed media as video-first  
FR8: Upload pinned videos once  
FR9: Treat deleted and reposted content as new  
FR10: Detect duplicates by post ID only  
FR11: Retry failed uploads once  
FR12: Mark posts as processed only after successful download and upload  
FR13: Use TikTok cookies for anti-block  
FR14: Rotate cookies on failure  
FR15: Implement conservative polling and random delays  
FR16: Load configuration and creators  
FR17: Store processed post IDs in SQLite state.db  

### NonFunctional Requirements

NFR1: Parallel downloads: 2-3  
NFR2: yt-dlp fragments: 1-2  
NFR3: Creators processed sequentially  
NFR4: Telegram uploads sequential  
NFR5: No recompression or recoding  
NFR6: Video: best available video + audio, merged to MP4 without re-encoding  
NFR7: Photos: original quality  
NFR8: Telegram bot must be admin to avoid auto-compression  
NFR9: No duplicate uploads  
NFR10: No missed content across restarts  
NFR11: Preserved quality  
NFR12: Clean recovery from sleep/reboot  
NFR13: Reliable operation on ChromeOS Crostini  
NFR14: Short-lived, stateless script runs  
NFR15: No always-on services, systemd, or Docker  

### Additional Requirements

- Use yt-dlp for metadata extraction to avoid fragile HTML parsing  
- Normalize posts to internal Post model with post_id, creator, kind, url, caption, created_at  
- Download media into structured folders  
- Use ThreadPoolExecutor(max_workers=2..3) for downloads  
- Upload files sequentially to avoid Telegram flood limits  
- Route uploads to chat + optional topic (message_thread_id)  
- Apply caption template: {original_caption}\n\n— @{creator}  
- For slideshows: sendMediaGroup, caption on first item only  
- SQLite schema with posts table including post_id, creator, kind, source_url, created_at, downloaded_at, uploaded_at, telegram_chat_id, telegram_message_id  
- Config files: config.yaml with fetch_depth, download_workers, yt_concurrent_fragments, retry_uploads, delay jitter ranges  
- Creators.yaml with username, chat_id, optional topic_id  
- Failure handling: rotate cookie on fetch fail, backoff; retry download once; retry upload once, don't mark state if fail  
- Use stdlib logging for observability  
- Store Telegram bot token in environment variable or .env file  
- Store TikTok cookies in cookies/ directory with chmod 600 permissions  
- Respect platform terms and applicable laws  

### FR Coverage Map

FR1: Epic 1 - Monitor specified TikTok creators for new content  
FR2: Epic 1 - Fetch latest 10 posts per creator  
FR3: Epic 1 - Sort posts oldest to newest  
FR4: Epic 2 - Download unseen posts  
FR5: Epic 3 - Upload videos to Telegram with best quality and caption + attribution  
FR6: Epic 3 - Upload slideshows as Telegram media groups with caption on first image  
FR7: Epic 2 - Handle mixed media as video-first  
FR8: Epic 2 - Upload pinned videos once  
FR9: Epic 2 - Treat deleted and reposted content as new  
FR10: Epic 2 - Detect duplicates by post ID only  
FR11: Epic 3 - Retry failed uploads once  
FR12: Epic 3 - Mark posts as processed only after successful download and upload  
FR13: Epic 5 - Use TikTok cookies for anti-block  
FR14: Epic 5 - Rotate cookies on failure  
FR15: Epic 5 - Implement conservative polling and random delays  
FR16: Epic 1 - Load configuration and creators  
FR17: Epic 4 - Store processed post IDs in SQLite state.db  

## Epic List

### Epic 1: Basic Monitoring Setup
Users can configure creators and monitor their TikTok feeds for new content, fetching and sorting posts chronologically.  
**FRs covered:** FR1, FR2, FR3, FR16.

### Epic 2: Content Download
Users can download new TikTok posts (videos, slideshows, mixed media) with best available quality, handling edge cases like pinned posts and reposts.  
**FRs covered:** FR4, FR7, FR8, FR9, FR10.

### Epic 3: Telegram Upload
Users can upload downloaded content to Telegram channels/topics with proper formatting, captions, and retry logic.  
**FRs covered:** FR5, FR6, FR11, FR12.

### Epic 4: State Persistence
Users can maintain processing state across restarts, ensuring no duplicates and reliable recovery from reboots.  
**FRs covered:** FR17.

### Epic 5: Anti-Bot Protection
Users can access TikTok content reliably using cookies, rotation, and conservative polling to avoid blocks.  
**FRs covered:** FR13, FR14, FR15.

## Epic 1: Basic Monitoring Setup
Users can configure creators and monitor their TikTok feeds for new content, fetching and sorting posts chronologically.  

### Story 1.1: Load Configuration and Creators
As a system administrator,  
I want to load configuration files (creators.yaml, config.yaml),  
So that the system knows which creators to monitor and operational parameters.  

**Acceptance Criteria:**  

**Given** valid config.yaml and creators.yaml files exist  
**When** the application starts  
**Then** all configuration parameters are loaded (fetch_depth, download_workers, etc.)  
**And** creators list with usernames, chat_ids, and optional topic_ids is available  

### Story 1.2: Fetch Latest Posts from TikTok
As a content monitor,  
I want to fetch the latest 10 posts per creator,  
So that new content can be identified.  

**Acceptance Criteria:**  

**Given** a valid creator username  
**When** fetching posts using yt-dlp metadata extraction  
**Then** retrieve up to 10 latest posts  
**And** normalize each to Post model with post_id, creator, kind, url, caption, created_at  

### Story 1.3: Sort Posts Chronologically
As a content processor,  
I want posts sorted from oldest to newest,  
So that content is processed in the correct order.  

**Acceptance Criteria:**  

**Given** a list of posts with created_at timestamps  
**When** sorting the posts  
**Then** posts are ordered by created_at ascending (oldest first)  
**And** posts without timestamps are handled appropriately

## Epic 2: Content Download
Users can download new TikTok posts (videos, slideshows, mixed media) with best available quality, handling edge cases like pinned posts and reposts.  

### Story 2.1: Check for Processed Posts
As a content processor,  
I want to check if a post has been processed before,  
So that duplicates are avoided across runs.  

**Acceptance Criteria:**  

**Given** a post_id and SQLite state.db exists  
**When** querying the posts table  
**Then** return true if post_id exists with uploaded_at set  
**And** return false if post_id does not exist or uploaded_at is null  

### Story 2.2: Download Video Content
As a downloader,  
I want to download video posts with best available quality,  
So that content is preserved without recompression.  

**Acceptance Criteria:**  

**Given** an unseen video post  
**When** downloading using yt-dlp  
**Then** use format "bv*+ba/best"  
**And** merge output to MP4 without re-encoding  
**And** limit concurrent fragments to 1-2  

### Story 2.3: Download Slideshow Content
As a downloader,  
I want to download slideshow images in original quality,  
So that photo content is available for upload.  

**Acceptance Criteria:**  

**Given** an unseen slideshow post  
**When** downloading images  
**Then** download all images in the slideshow  
**And** preserve original quality  
**And** save to structured download folders  

### Story 2.4: Handle Download Edge Cases
As a robust downloader,  
I want to handle pinned posts, reposts, and mixed media correctly,  
So that all content types are processed appropriately.  

**Acceptance Criteria:**  

**Given** a pinned post  
**When** processing for download  
**Then** download once regardless of pin status  

**Given** deleted and reposted content  
**When** processing  
**Then** treat as new post based on current post_id  

**Given** mixed media post  
**When** processing  
**Then** prioritize video download over photos

## Epic 3: Telegram Upload
Users can upload downloaded content to Telegram channels/topics with proper formatting, captions, and retry logic.  

### Story 3.1: Upload Video Content
As a Telegram uploader,  
I want to upload videos with attribution captions,  
So that content appears correctly in channels.  

**Acceptance Criteria:**  

**Given** a downloaded video file and Telegram bot token  
**When** uploading using sendVideo  
**Then** upload the MP4 file  
**And** set caption to "{original_caption}\n\n— @{creator}"  
**And** ensure bot has admin rights to avoid compression  

### Story 3.2: Upload Slideshow as Media Group
As a Telegram uploader,  
I want to upload slideshows as media groups with proper captions,  
So that images appear as albums.  

**Acceptance Criteria:**  

**Given** downloaded slideshow images  
**When** uploading using sendMediaGroup  
**Then** include all images in the group  
**And** set caption on the first media item only  
**And** preserve image order  

### Story 3.3: Implement Upload Retry Logic
As a reliable uploader,  
I want to retry failed uploads once,  
So that transient failures don't cause content loss.  

**Acceptance Criteria:**  

**Given** an upload attempt fails  
**When** handling the failure  
**Then** retry the upload once  
**And** only mark post as processed if upload succeeds  
**And** log failure details for debugging  

### Story 3.4: Route Uploads to Specified Destinations
As a channel manager,  
I want uploads routed to correct chats and topics,  
So that content reaches the intended audience.  

**Acceptance Criteria:**  

**Given** creator config with chat_id and optional topic_id  
**When** uploading content  
**Then** send to the specified chat_id  
**And** include message_thread_id if topic is configured  
**And** store telegram_chat_id and telegram_message_id in state
## Epic 4: State Persistence
Users can maintain processing state across restarts, ensuring no duplicates and reliable recovery from reboots.

### Story 4.1: Store Processed Post IDs in SQLite State DB
As a state manager,
I want to store processed post IDs in SQLite state.db,
So that duplicates are avoided across restarts.

**Acceptance Criteria:**

**Given** a post has been processed
**When** storing state
**Then** create/update SQLite posts table with post details
**And** include post_id, creator, kind, source_url, created_at, downloaded_at, uploaded_at, telegram_chat_id, telegram_message_id
**And** ensure reliable recovery from reboots

## Epic 5: Anti-Bot Protection
Users can access TikTok content reliably using cookies, rotation, and conservative polling to avoid blocks.

### Story 5.1: Use TikTok Cookies for Anti-Block
As an anti-block system,
I want to use TikTok cookies for requests,
So that access is not blocked by TikTok.

**Acceptance Criteria:**

**Given** TikTok cookies are available
**When** making requests to TikTok
**Then** include cookies in requests
**And** store cookies securely in cookies/ directory
**And** set permissions to 600

### Story 5.2: Rotate Cookies on Failure
As an anti-block system,
I want to rotate cookies on failure,
So that blocked cookies don't prevent access.

**Acceptance Criteria:**

**Given** a fetch request fails due to blocking
**When** handling the failure
**Then** switch to the next available cookie
**And** retry the request with the new cookie
**And** log the rotation for monitoring

### Story 5.3: Implement Conservative Polling and Random Delays
As an anti-block system,
I want to implement conservative polling and random delays,
So that requests appear human-like and avoid detection.

**Acceptance Criteria:**

**Given** polling configuration
**When** fetching posts from creators
**Then** add random delays between requests
**And** limit polling frequency
**And** configure delay ranges in config.yaml
