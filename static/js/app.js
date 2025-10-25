// Global state
let currentSessionId = null;
let currentCarouselIndex = 0;
let carouselPosts = [];
let statusCheckInterval = null;

// Page navigation
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
}

// Form submission
document.getElementById('analyze-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const profileUrl = document.getElementById('profile-url').value.trim();

    if (!profileUrl) {
        alert('Please enter a profile URL or username');
        return;
    }

    // Start analysis
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                profile_url: profileUrl,
                results_limit: 30
            })
        });

        if (!response.ok) {
            throw new Error('Failed to start analysis');
        }

        const data = await response.json();
        currentSessionId = data.session_id;

        // Show loading page
        document.getElementById('loading-username').textContent = `@${data.username}`;
        showPage('loading-page');

        // Start polling for status
        startStatusPolling();

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to start analysis. Please try again.');
    }
});

// Status polling
function startStatusPolling() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    statusCheckInterval = setInterval(checkStatus, 2000);
    checkStatus(); // Check immediately
}

async function checkStatus() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`/api/status/${currentSessionId}`);
        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const data = await response.json();

        // Update progress
        updateProgress(data.progress, data.message);

        // Update carousel if posts are available
        if (data.posts_preview && data.posts_preview.length > 0) {
            if (carouselPosts.length === 0) {
                carouselPosts = data.posts_preview;
                initCarousel();
            }
        }

        // Check if completed
        if (data.status === 'completed') {
            clearInterval(statusCheckInterval);
            setTimeout(() => {
                loadReport();
            }, 1000);
        } else if (data.status === 'error') {
            clearInterval(statusCheckInterval);
            alert(`Error: ${data.error}`);
            showPage('landing-page');
        }

    } catch (error) {
        console.error('Status check error:', error);
    }
}

function updateProgress(progress, message) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const loadingMessage = document.getElementById('loading-message');

    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    loadingMessage.textContent = message;
}

// Carousel
function initCarousel() {
    const carouselContainer = document.getElementById('carousel-container');
    const carouselTrack = document.getElementById('carousel-track');

    carouselContainer.style.display = 'block';
    carouselTrack.innerHTML = '';

    carouselPosts.forEach((post, index) => {
        const item = document.createElement('div');
        item.className = 'carousel-item';

        const imageUrl = post.images && post.images[0] ? post.images[0] : 'https://via.placeholder.com/800x400?text=No+Image';
        const caption = post.caption || 'No caption';

        item.innerHTML = `
            <img src="${imageUrl}" alt="Post ${index + 1}">
            <div class="carousel-caption">
                <p>${caption.substring(0, 150)}${caption.length > 150 ? '...' : ''}</p>
            </div>
        `;

        carouselTrack.appendChild(item);
    });

    currentCarouselIndex = 0;
    updateCarousel();
}

function moveCarousel(direction) {
    currentCarouselIndex += direction;

    if (currentCarouselIndex < 0) {
        currentCarouselIndex = carouselPosts.length - 1;
    } else if (currentCarouselIndex >= carouselPosts.length) {
        currentCarouselIndex = 0;
    }

    updateCarousel();
}

function updateCarousel() {
    const track = document.getElementById('carousel-track');
    const offset = -currentCarouselIndex * 100;
    track.style.transform = `translateX(${offset}%)`;
}

// Load report
async function loadReport() {
    try {
        const response = await fetch(`/api/report/${currentSessionId}`);
        if (!response.ok) {
            throw new Error('Failed to load report');
        }

        const report = await response.json();
        renderReport(report);
        showPage('report-page');

    } catch (error) {
        console.error('Error loading report:', error);
        alert('Failed to load report. Please try again.');
    }
}

function renderReport(report) {
    // Render profile summary
    renderProfileSummary(report);

    // Render summary section
    renderSummarySection(report);

    // Render detailed report
    renderDetailedReport(report);

    // Render posts gallery
    renderPostsGallery(report);
}

function renderProfileSummary(report) {
    const summaryContainer = document.getElementById('profile-summary');
    const profile = report.profile;

    summaryContainer.innerHTML = `
        ${profile.profile_pic_url ? `<img src="${profile.profile_pic_url}" alt="Profile" class="profile-avatar">` : ''}
        <div class="profile-info">
            <h2>${profile.full_name || profile.username}</h2>
            <p class="profile-username">@${report.username}</p>
            ${profile.website ? `<p><a href="${profile.website}" target="_blank" style="color: var(--primary);">🔗 ${profile.website}</a></p>` : ''}
            <div class="profile-stats">
                <div class="stat">
                    <span class="stat-value">${report.posts.length}</span>
                    <span class="stat-label">Posts Analyzed</span>
                </div>
            </div>
        </div>
    `;
}

function renderSummarySection(report) {
    const summaryContainer = document.getElementById('summary-section');
    const summary = report.analysis?.summary || {};

    summaryContainer.innerHTML = `
        <h2 class="section-title">Summary</h2>

        <div class="summary-box">
            <h3>One-Sentence Summary</h3>
            <p style="font-size: 1.15rem; color: var(--text);">${summary.one_sentence || 'No summary available'}</p>
        </div>

        <div class="summary-box">
            <h3>Conversation Openers</h3>
            <ul class="openers-list">
                ${(summary.openers || []).map(opener => `<li>💬 ${opener}</li>`).join('')}
            </ul>
        </div>

        <div class="summary-box">
            <h3>Keywords</h3>
            <div class="keywords">
                ${(summary.keywords || []).map(keyword => `<span class="keyword-tag">${keyword}</span>`).join('')}
            </div>
        </div>
    `;
}

function renderDetailedReport(report) {
    const detailedContainer = document.getElementById('detailed-report');
    const detailed = report.analysis?.detailed_report || {};

    let html = '<h2 class="section-title">Detailed Analysis</h2>';

    // Name and Handle
    if (detailed.name_and_handle) {
        html += `
            <div class="detail-item">
                <h3>👤 Name & Handle</h3>
                <p>${detailed.name_and_handle}</p>
            </div>
        `;
    }

    // Intro and Websites
    if (detailed.intro_and_websites) {
        html += `
            <div class="detail-item">
                <h3>📝 Intro & Personal Websites</h3>
                <p>${detailed.intro_and_websites}</p>
            </div>
        `;
    }

    // Interests and Hobbies
    if (detailed.interests_and_hobbies) {
        html += `
            <div class="detail-item">
                <h3>🎯 Interests & Hobbies</h3>
                <p>${detailed.interests_and_hobbies}</p>
            </div>
        `;
    }

    // Relationship Status
    if (detailed.relationship_status) {
        const relStatus = detailed.relationship_status;
        html += `
            <div class="detail-item">
                <h3>💕 Relationship Status</h3>
                <p><strong>Status:</strong> ${relStatus.status || 'Unknown'}</p>
                <p>${relStatus.evidence || ''}</p>
                <div class="confidence-bar">
                    <div class="confidence-label">
                        <span>Confidence</span>
                        <span>${relStatus.confidence || 0}%</span>
                    </div>
                    <div class="confidence-fill">
                        <div class="confidence-fill-bar" style="width: ${relStatus.confidence || 0}%"></div>
                    </div>
                </div>
            </div>
        `;
    }

    // Personality
    if (detailed.personality) {
        const personality = detailed.personality;
        html += `
            <div class="detail-item">
                <h3>🧠 Personality Analysis</h3>
                <p><strong>MBTI Type:</strong> ${personality.mbti || 'Unknown'}</p>
                <p>${personality.analysis || ''}</p>
                <div class="confidence-bar">
                    <div class="confidence-label">
                        <span>Confidence</span>
                        <span>${personality.confidence || 0}%</span>
                    </div>
                    <div class="confidence-fill">
                        <div class="confidence-fill-bar" style="width: ${personality.confidence || 0}%"></div>
                    </div>
                </div>
            </div>
        `;
    }

    // Overall Presence
    if (detailed.overall_presence) {
        html += `
            <div class="detail-item">
                <h3>✨ Overall Presence & Vibe</h3>
                <p>${detailed.overall_presence}</p>
            </div>
        `;
    }

    // Life Attitude
    if (detailed.life_attitude) {
        html += `
            <div class="detail-item">
                <h3>🌟 Attitude Towards Life</h3>
                <p>${detailed.life_attitude}</p>
            </div>
        `;
    }

    // Notable Insights
    if (detailed.notable_insights) {
        html += `
            <div class="detail-item">
                <h3>💡 Notable Insights</h3>
                <p>${detailed.notable_insights}</p>
            </div>
        `;
    }

    detailedContainer.innerHTML = html;
}

function renderPostsGallery(report) {
    const postsGrid = document.getElementById('posts-grid');
    const posts = report.posts || [];

    postsGrid.innerHTML = posts.map((post, index) => {
        const collageUrl = post.collage_path ? `/collages/${post.collage_path.split('/').pop()}` : null;
        const imageUrl = collageUrl || (post.images && post.images[0] ? post.images[0].url : 'https://via.placeholder.com/300x300?text=No+Image');
        const caption = post.caption || 'No caption';
        const postType = post.type || 'Unknown';

        return `
            <div class="post-card">
                <img src="${imageUrl}" alt="Post ${index + 1}" class="post-image" onerror="this.src='https://via.placeholder.com/300x300?text=Image+Not+Available'">
                <div class="post-info">
                    <span class="post-type">${postType}</span>
                    <div class="post-meta">
                        <span>❤️ ${post.likesCount || 0}</span>
                        <span>💬 ${post.commentsCount || 0}</span>
                        ${post.videoViewCount ? `<span>👁️ ${post.videoViewCount}</span>` : ''}
                    </div>
                    <p class="post-caption">${caption.substring(0, 150)}${caption.length > 150 ? '...' : ''}</p>
                    ${post.url ? `<a href="${post.url}" target="_blank" style="color: var(--primary); font-size: 0.9rem;">View on Instagram →</a>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Initialize
console.log('Instagram Profile Analyzer loaded');
