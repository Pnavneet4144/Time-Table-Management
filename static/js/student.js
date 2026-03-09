requireAuth('student');

let currentFormId = null;
let currentQuestions = [];
let currentAnswers = {};

document.addEventListener('DOMContentLoaded', () => {
  const username = getUsername();
  document.getElementById('sidebarUsername').textContent = username || 'Student';
  document.getElementById('userAvatar').textContent = (username || 'S')[0].toUpperCase();
  document.getElementById('topbarDate').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  loadStudentTimetable();
  loadFeedbackForms();
});

function showSection(name, el) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`section-${name}`).classList.add('active');
  if (el) el.classList.add('active');
  const titles = {
    'timetable': 'My Timetable',
    'feedback': 'Feedback Forms',
    'change-password': 'Change Password'
  };
  document.getElementById('topbarTitle').textContent = titles[name] || name;
}

async function loadStudentTimetable() {
  const container = document.getElementById('studentTimetableGrid');
  try {
    const entries = await apiRequest('/student/timetable');
    if (!entries.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><p>No timetable entries available yet.</p></div>';
      return;
    }
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const daysPresent = days.filter(d => entries.some(e => e.day_of_week === d));
    const timeSlots = [...new Set(entries.map(e => `${e.start_time}|${e.end_time}`))].sort();
    const entryMap = {};
    entries.forEach(e => {
      const key = `${e.day_of_week}|${e.start_time}|${e.end_time}`;
      if (!entryMap[key]) entryMap[key] = [];
      entryMap[key].push(e);
    });
    let html = '<table class="tt-table"><thead><tr><th>Time</th>' + daysPresent.map(d => `<th>${d}</th>`).join('') + '</tr></thead><tbody>';
    timeSlots.forEach(slot => {
      const [st, et] = slot.split('|');
      html += `<tr><td style="white-space:nowrap;font-size:0.8rem;color:#546e7a;padding:0.75rem 0.6rem">${st}<br>—<br>${et}</td>`;
      daysPresent.forEach(day => {
        const key = `${day}|${st}|${et}`;
        const cells = entryMap[key] || [];
        html += '<td class="tt-cell">';
        cells.forEach(c => {
          html += `<div class="tt-entry">
            <strong>${c.subject_code}</strong>
            <div style="font-size:0.75rem;color:#37474f">${c.subject_name}</div>
            <small>${c.room_number} · ${c.section}</small>
            <small style="display:block;color:#90a4ae;margin-top:2px">${c.coordinator_name}</small>
          </div>`;
        });
        html += '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p style="color:#c62828">${e.message}</p></div>`;
  }
}

async function downloadTimetablePDF() {
  try {
    const token = getToken();
    const res = await fetch('/student/timetable/pdf', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Failed to generate PDF');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'my_timetable.pdf';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Timetable PDF downloaded!', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function loadFeedbackForms() {
  const container = document.getElementById('feedbackFormsContainer');
  try {
    const assignments = await apiRequest('/student/feedback/forms');
    if (!assignments.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><p>No feedback forms assigned to you yet.</p></div>';
      return;
    }
    container.innerHTML = assignments.map(a => `
      <div class="card" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem">
        <div>
          <div style="font-family:'Playfair Display',serif;font-size:1.05rem;font-weight:700;color:#1a237e;margin-bottom:0.3rem">${a.form_title}</div>
          <div style="font-size:0.8rem;color:#90a4ae">Assigned: ${formatDate(a.assigned_at)} · ${a.questions.length} question${a.questions.length !== 1 ? 's' : ''}</div>
        </div>
        <div style="display:flex;align-items:center;gap:1rem">
          <span class="badge ${a.is_completed ? 'badge-completed' : 'badge-pending'}">${a.is_completed ? '✓ Completed' : '⏳ Pending'}</span>
          ${!a.is_completed ? `<button class="action-btn btn-blue btn-sm" onclick="openFeedbackForm(${a.form_id}, '${a.form_title.replace(/'/g, "\\'")}', ${JSON.stringify(a.questions).replace(/"/g, '&quot;')})">Fill Form</button>` : '<span style="font-size:0.8rem;color:#90a4ae">Submitted</span>'}
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p style="color:#c62828">${e.message}</p></div>`;
  }
}

function openFeedbackForm(formId, formTitle, questions) {
  currentFormId = formId;
  currentQuestions = questions;
  currentAnswers = {};
  document.getElementById('modalFormTitle').textContent = formTitle;
  const body = document.getElementById('modalFormBody');
  body.innerHTML = questions.map((q, idx) => buildQuestionHTML(q, idx)).join('');
  document.getElementById('feedbackModal').style.display = 'block';
  document.body.style.overflow = 'hidden';
}

function buildQuestionHTML(question, idx) {
  const num = idx + 1;
  if (question.question_type === 'rating') {
    const stars = [1, 2, 3, 4, 5].map(n =>
      `<button type="button" class="star-btn" onclick="setRating(${question.id}, ${n})" id="star_${question.id}_${n}">${n}</button>`
    ).join('');
    return `
      <div class="feedback-question">
        <div class="fq-label"><span class="fq-num">${num}</span><span>${question.question_text}</span></div>
        <div class="rating-stars" id="ratingGroup_${question.id}">${stars}</div>
      </div>
    `;
  }
  if (question.question_type === 'text') {
    return `
      <div class="feedback-question">
        <div class="fq-label"><span class="fq-num">${num}</span><span>${question.question_text}</span></div>
        <textarea rows="3" style="width:100%;padding:0.65rem 0.9rem;border:1.5px solid #e8eaf6;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.9rem;resize:vertical;outline:none"
          placeholder="Your answer..." oninput="currentAnswers[${question.id}] = this.value"
          onfocus="this.style.borderColor='#5c6bc0'" onblur="this.style.borderColor='#e8eaf6'"></textarea>
      </div>
    `;
  }
  if (question.question_type === 'mcq') {
    const opts = (question.options || []).map(opt =>
      `<div class="mcq-option" onclick="setMCQ(${question.id}, '${opt.replace(/'/g, "\\'")}', this)" data-value="${opt}">
        <input type="radio" name="mcq_${question.id}" value="${opt}" /> ${opt}
      </div>`
    ).join('');
    return `
      <div class="feedback-question">
        <div class="fq-label"><span class="fq-num">${num}</span><span>${question.question_text}</span></div>
        <div class="mcq-options">${opts}</div>
      </div>
    `;
  }
  return '';
}

function setRating(questionId, value) {
  currentAnswers[questionId] = String(value);
  for (let i = 1; i <= 5; i++) {
    const btn = document.getElementById(`star_${questionId}_${i}`);
    if (btn) btn.classList.toggle('selected', i <= value);
  }
}

function setMCQ(questionId, value, el) {
  currentAnswers[questionId] = value;
  const parent = el.closest('.mcq-options');
  parent.querySelectorAll('.mcq-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
}

function closeModal() {
  document.getElementById('feedbackModal').style.display = 'none';
  document.body.style.overflow = '';
  currentFormId = null;
  currentQuestions = [];
  currentAnswers = {};
}

async function submitFeedback() {
  for (const q of currentQuestions) {
    if (!currentAnswers[q.id] && currentAnswers[q.id] !== '0') {
      showToast(`Please answer question: "${q.question_text.substring(0, 40)}..."`, 'error');
      return;
    }
  }
  const answers = Object.entries(currentAnswers).map(([question_id, answer]) => ({
    question_id: parseInt(question_id),
    answer
  }));
  const btn = document.getElementById('modalSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';
  try {
    await apiRequest(`/student/feedback/submit/${currentFormId}`, {
      method: 'POST',
      body: JSON.stringify({ answers })
    });
    showToast('Feedback submitted successfully!', 'success');
    closeModal();
    loadFeedbackForms();
  } catch (e) {
    showToast(e.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Submit Feedback';
  }
}


async function changeMyPassword() {
  const oldPassword = document.getElementById('oldPassword').value.trim();
  const newPassword = document.getElementById('newPassword').value.trim();
  const confirmNewPassword = document.getElementById('confirmNewPassword').value.trim();
  const errorDiv = document.getElementById('changePasswordError');
  const successDiv = document.getElementById('changePasswordSuccess');

  errorDiv.style.display = 'none';
  successDiv.style.display = 'none';

  if (!oldPassword) { errorDiv.textContent = 'Please enter your current password.'; errorDiv.style.display = 'block'; return; }
  if (!newPassword) { errorDiv.textContent = 'Please enter a new password.'; errorDiv.style.display = 'block'; return; }
  if (newPassword.length < 6) { errorDiv.textContent = 'New password must be at least 6 characters.'; errorDiv.style.display = 'block'; return; }
  if (newPassword !== confirmNewPassword) { errorDiv.textContent = 'Passwords do not match.'; errorDiv.style.display = 'block'; return; }
  if (oldPassword === newPassword) { errorDiv.textContent = 'New password must be different from current password.'; errorDiv.style.display = 'block'; return; }

  try {
    await apiRequest('/admin/change-my-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    successDiv.textContent = 'Password changed successfully! Logging you out in 3 seconds...';
    successDiv.style.display = 'block';
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmNewPassword').value = '';
    setTimeout(() => logout(), 3000);
  } catch (e) {
    errorDiv.textContent = e.message;
    errorDiv.style.display = 'block';
  }
}