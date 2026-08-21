// 培训管理系统 - 智能推荐前端
const API = '';
let currentUser = null;
let currentAlgo = 'hybrid';
let currentCourse = null;
let allCourses = [];

// 头像颜色池
const AVATAR_COLORS = [
    '#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
    '#EC4899', '#06B6D4', '#F97316', '#6366F1', '#14B8A6'
];

// ===== 初始化 =====
async function init() {
    await loadUsers();
    await loadCourses();
    bindEvents();
}

async function loadUsers() {
    const res = await fetch(`${API}/api/users`);
    const users = await res.json();
    const list = document.getElementById('userList');
    list.innerHTML = users.map(u => `
        <div class="user-item" data-id="${u.id}">
            <div class="user-avatar" style="background:${AVATAR_COLORS[u.id % 10]}">${u.avatar}</div>
            <div class="user-info">
                <div class="user-name">${u.name}</div>
                <div class="user-dept">${u.department} · ${u.learned_count}门课</div>
            </div>
        </div>
    `).join('');
    list.querySelectorAll('.user-item').forEach(el => {
        el.onclick = () => selectUser(parseInt(el.dataset.id));
    });
}

async function loadCourses() {
    const res = await fetch(`${API}/api/courses`);
    allCourses = await res.json();
}

function bindEvents() {
    document.querySelectorAll('.algo-tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.algo-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentAlgo = tab.dataset.algo;
            if (currentUser) loadRecommendations();
        };
    });
}

// ===== 选择用户 =====
async function selectUser(userId) {
    currentUser = userId;
    document.querySelectorAll('.user-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.id) === userId);
    });

    document.getElementById('welcomeBanner').style.display = 'none';
    document.getElementById('userBanner').style.display = 'flex';
    document.getElementById('algoTabs').style.display = 'grid';
    document.getElementById('recommendSection').style.display = 'block';
    document.getElementById('learnedSection').style.display = 'block';
    document.getElementById('compareSection').style.display = 'block';
    document.getElementById('profilePanel').style.display = 'block';

    await Promise.all([
        loadRecommendations(),
        loadProfile(),
        loadLearnedCourses()
    ]);
}

// ===== 加载推荐 =====
async function loadRecommendations() {
    const grid = document.getElementById('recommendGrid');
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#9CA3AF;">推荐计算中...</div>';

    const res = await fetch(`${API}/api/recommend/${currentUser}?algorithm=${currentAlgo}&top_n=8`);
    const data = await res.json();

    // 更新标题
    const titles = {
        hybrid: '🎯 为你智能推荐',
        user_cf: '👥 相似学员在学',
        item_cf: '🔗 你可能感兴趣的课程',
        content: '🏷️ 根据你的兴趣推荐',
        popular: '🔥 热门课程排行'
    };
    document.getElementById('sectionTitle').textContent = titles[currentAlgo] || '为你推荐';
    document.getElementById('sectionSub').textContent = data.algorithm_name;

    // 更新用户横幅
    const p = data.profile;
    document.getElementById('userName').textContent = p.user.name;
    document.getElementById('userDept').textContent = `${p.user.department} · ${p.user.position}`;
    document.getElementById('userAvatarLg').textContent = p.user.avatar;
    document.getElementById('userAvatarLg').style.background = AVATAR_COLORS[currentUser % 10];
    document.getElementById('learnedCount').textContent = p.learned_count;
    document.getElementById('totalProgress').textContent = Math.round(p.total_progress);
    document.getElementById('coldStartBadge').style.display = p.is_cold_start ? 'block' : 'none';

    if (!data.recommendations.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#9CA3AF;">暂无推荐结果</div>';
        return;
    }

    grid.innerHTML = data.recommendations.map(c => renderCourseCard(c, true)).join('');
    bindCardClicks(grid);
}

// ===== 加载用户画像 =====
async function loadProfile() {
    const res = await fetch(`${API}/api/profile/${currentUser}`);
    const p = await res.json();
    const el = document.getElementById('profileContent');

    let html = `
        <div class="profile-stat">
            <span>已学课程</span>
            <span class="profile-stat-val">${p.learned_count} 门</span>
        </div>
        <div class="profile-stat">
            <span>学习总时长</span>
            <span class="profile-stat-val">${Math.round(p.total_progress)} h</span>
        </div>
    `;
    if (p.top_categories.length) {
        html += `
            <div class="profile-row">
                <div class="profile-label">偏好分类</div>
                <div class="profile-tags">
                    ${p.top_categories.map(c => `<span class="profile-tag">${c}</span>`).join('')}
                </div>
            </div>
        `;
    }
    if (p.top_tags.length) {
        html += `
            <div class="profile-row">
                <div class="profile-label">兴趣标签</div>
                <div class="profile-tags">
                    ${p.top_tags.map(t => `<span class="profile-tag">${t}</span>`).join('')}
                </div>
            </div>
        `;
    }
    if (p.is_cold_start) {
        html += `<div style="margin-top:8px;padding:8px;background:#FEF3C7;border-radius:6px;font-size:11px;color:#92400E;">⚠️ 新用户冷启动：推荐以热门+内容为主，多学习课程后推荐更精准</div>`;
    }
    el.innerHTML = html;
}

// ===== 已学课程 =====
async function loadLearnedCourses() {
    const res = await fetch(`${API}/api/profile/${currentUser}`);
    const p = await res.json();
    const grid = document.getElementById('learnedGrid');

    if (!p.learned_courses.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:20px;color:#9CA3AF;">暂无学习记录</div>';
        return;
    }

    grid.innerHTML = p.learned_courses.map(c => `
        <div class="course-card" data-id="${c.id}">
            <div class="course-cover" style="background:${c.cover_color}">
                <span class="course-cover-text">${c.name}</span>
            </div>
            <div class="course-body">
                <div class="course-name">${c.name}</div>
                <div class="course-tags">
                    ${c.categories.slice(0,1).map(t => `<span class="course-tag">${t}</span>`).join('')}
                    ${c.tags.slice(0,2).map(t => `<span class="course-tag">${t}</span>`).join('')}
                </div>
                <div style="font-size:11px;color:#6B7280;">学习进度 ${Math.round(c.progress * 100)}%</div>
                <div class="progress-bar"><div class="progress-fill" style="width:${c.progress * 100}%"></div></div>
                <div class="course-meta" style="margin-top:6px;">
                    <span>${c.rating > 0 ? '<span class="rating-stars">' + '★'.repeat(c.rating) + '☆'.repeat(5-c.rating) + '</span>' : '未评价'}</span>
                </div>
            </div>
        </div>
    `).join('');
    bindCardClicks(grid);
}

// ===== 渲染课程卡片 =====
function renderCourseCard(c, showReason) {
    const scorePct = Math.min(100, Math.round(c.score * 100));
    return `
        <div class="course-card" data-id="${c.id}">
            <div class="course-cover" style="background:${c.cover_color}">
                <span class="course-difficulty">${c.difficulty}</span>
                <span class="course-cover-text">${c.name}</span>
            </div>
            <div class="course-body">
                <div class="course-name">${c.name}</div>
                <div class="course-desc">${c.desc}</div>
                <div class="course-tags">
                    ${c.categories.slice(0,1).map(t => `<span class="course-tag">${t}</span>`).join('')}
                    ${c.tags.slice(0,2).map(t => `<span class="course-tag">${t}</span>`).join('')}
                </div>
                ${showReason && c.reason ? `<div class="course-reason">💡 ${c.reason}</div>` : ''}
                <div class="course-meta">
                    <span>${c.instructor} · ${c.duration}h</span>
                    <span class="course-score">
                        <span class="score-bar"><span class="score-bar-fill" style="width:${scorePct}%"></span></span>
                        ${(c.score * 100).toFixed(0)}%
                    </span>
                </div>
            </div>
        </div>
    `;
}

function bindCardClicks(container) {
    container.querySelectorAll('.course-card').forEach(card => {
        card.onclick = () => openCourseModal(parseInt(card.dataset.id));
    });
}

// ===== 课程详情弹窗 =====
function openCourseModal(courseId) {
    currentCourse = allCourses.find(c => c.id === courseId);
    if (!currentCourse) return;

    const isLearned = !!(currentUser && engine_learned_has(courseId));

    document.getElementById('modalTitle').textContent = currentCourse.name;
    document.getElementById('modalDesc').textContent = currentCourse.desc;
    document.getElementById('modalCover').style.background = currentCourse.cover_color;
    document.getElementById('modalCover').textContent = currentCourse.name;
    document.getElementById('modalMeta').innerHTML = `
        <span class="meta-chip">📚 ${currentCourse.categories.join(' / ')}</span>
        <span class="meta-chip">🎯 ${currentCourse.difficulty}</span>
        <span class="meta-chip">⏱ ${currentCourse.duration} 小时</span>
        <span class="meta-chip">👨‍🏫 ${currentCourse.instructor}</span>
        <span class="meta-chip">👥 ${currentCourse.learners} 人学习</span>
    `;

    // 推荐理由
    const reasonEl = document.getElementById('modalReason');
    const recCard = document.querySelector(`#recommendGrid .course-card[data-id="${courseId}"]`);
    if (recCard) {
        const reasonDiv = recCard.querySelector('.course-reason');
        reasonEl.style.display = reasonDiv ? 'block' : 'none';
        reasonEl.textContent = reasonDiv ? '💡 ' + reasonDiv.textContent.replace('💡 ', '') : '';
    } else {
        reasonEl.style.display = 'none';
    }

    document.getElementById('btnLearn').textContent = isLearned ? '继续学习' : '开始学习';
    document.getElementById('ratingPicker').style.display = 'none';
    document.getElementById('courseModal').classList.add('show');
}

function engine_learned_has(courseId) {
    // 从已学课程区域判断
    const el = document.querySelector(`#learnedGrid .course-card[data-id="${courseId}"]`);
    return !!el;
}

function closeModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('courseModal').classList.remove('show');
}

// ===== 开始学习（模拟学习行为，实时更新推荐）=====
async function startLearning() {
    if (!currentUser || !currentCourse) return;

    // 模拟学习进度和行为
    const progress = Math.random() * 0.5 + 0.3; // 30%-80%
    const behaviorWeight = 0.7;

    const res = await fetch(`${API}/api/interact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: currentUser,
            course_id: currentCourse.id,
            progress: progress,
            rating: 0,
            behavior_weight: behaviorWeight
        })
    });
    const data = await res.json();

    if (data.success) {
        showToast('✅ 学习行为已记录，推荐结果已实时更新！');
        closeModal();
        await Promise.all([
            loadRecommendations(),
            loadProfile(),
            loadLearnedCourses()
        ]);
    }
}

// ===== 评分 =====
function showRating() {
    const picker = document.getElementById('ratingPicker');
    picker.style.display = 'block';
    const starsEl = document.getElementById('stars');
    starsEl.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.textContent = '★';
        star.dataset.value = i;
        star.onmouseenter = () => highlightStars(i);
        star.onmouseleave = () => highlightStars(0);
        star.onclick = () => submitRating(i);
        starsEl.appendChild(star);
    }
}

function highlightStars(n) {
    document.querySelectorAll('#stars .star').forEach((s, i) => {
        s.classList.toggle('active', i < n);
    });
}

async function submitRating(rating) {
    if (!currentUser || !currentCourse) return;
    const res = await fetch(`${API}/api/interact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: currentUser,
            course_id: currentCourse.id,
            progress: 0.5,
            rating: rating,
            behavior_weight: 0.8
        })
    });
    const data = await res.json();
    if (data.success) {
        showToast(`⭐ 已给出 ${rating} 星评价，推荐已更新！`);
        closeModal();
        await Promise.all([
            loadRecommendations(),
            loadProfile(),
            loadLearnedCourses()
        ]);
    }
}

// ===== 算法对比 =====
async function runCompare() {
    if (!currentUser) return;
    const grid = document.getElementById('compareGrid');
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:20px;color:#9CA3AF;">正在运行全部算法对比...</div>';

    const res = await fetch(`${API}/api/compare/${currentUser}?top_n=5`);
    const data = await res.json();

    const algoIcons = {
        hybrid: '🔀', user_cf: '👥', item_cf: '🔗', content: '🏷️', popular: '🔥'
    };

    grid.innerHTML = Object.entries(data).map(([key, val]) => {
        // 对每个算法的分数做归一化显示
        const scores = val.courses.map(c => c.score);
        const sMin = Math.min(...scores), sMax = Math.max(...scores);
        const sRange = sMax - sMin || 1;
        return `
        <div class="compare-card">
            <h4>${algoIcons[key] || ''} ${val.name}</h4>
            ${val.courses.map((c, i) => {
                const normPct = Math.round(((c.score - sMin) / sRange) * 100);
                return `
                <div class="compare-item">
                    <span class="compare-rank ${i < 3 ? 'top3' : ''}">${i + 1}</span>
                    <span class="compare-name">${c.name}</span>
                    <span class="compare-score">${normPct}%</span>
                </div>
            `}).join('')}
        </div>
    `}).join('');
}

// ===== Toast =====
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// 启动
init();
