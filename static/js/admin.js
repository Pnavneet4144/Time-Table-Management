requireAuth('admin');

let allSubjects = [];
let allRooms = [];
let allForms = [];
let allStudents = [];

document.addEventListener('DOMContentLoaded', () => {
  const username = getUsername();
  document.getElementById('sidebarUsername').textContent = username || 'Admin';
  document.getElementById('userAvatar').textContent = (username || 'A')[0].toUpperCase();
  document.getElementById('topbarDate').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  loadSubjects();
  loadRooms();
  loadForms();
  loadStudents();
});

function showSection(name, el) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`section-${name}`).classList.add('active');
  if (el) el.classList.add('active');
  const titles = {
    'subjects': 'Manage Subjects', 'rooms': 'Manage Rooms', 'timetable': 'Build Timetable',
    'view-timetable': 'View Timetable', 'create-feedback': 'Create Feedback Form',
    'share-feedback': 'Share Feedback', 'view-responses': 'View Responses',
    'reset-password': 'Reset Student Password'
  };
  document.getElementById('topbarTitle').textContent = titles[name] || name;
  if (name === 'view-timetable') renderTimetableGrid();
  if (name === 'timetable') { populateTimetableSelects(); loadTimetableEntries(); }
  if (name === 'share-feedback') populateShareFormSelect();
  if (name === 'view-responses') populateResponseFormSelect();
  if (name === 'reset-password') populateResetPasswordSection();

  // Logo preview
  const logoInput = document.getElementById('pdfLogo');
  if (logoInput && !logoInput._listenerAdded) {
    logoInput._listenerAdded = true;
    logoInput.addEventListener('change', () => {
      const file = logoInput.files[0];
      const previewBox = document.getElementById('logoPreviewBox');
      const preview    = document.getElementById('logoPreview');
      if (file) {
        const reader = new FileReader();
        reader.onload = e => { preview.src = e.target.result; previewBox.style.display = 'block'; };
        reader.readAsDataURL(file);
      } else {
        previewBox.style.display = 'none';
      }
    });
  }
}

async function loadSubjects() {
  try {
    allSubjects = await apiRequest('/admin/subjects');
    renderSubjectsTable();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderSubjectsTable() {
  const tbody = document.getElementById('subjectsTable');
  if (!allSubjects.length) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">📚</div><p>No subjects added yet.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = allSubjects.map((s, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${s.name}</strong></td>
      <td><code>${s.code}</code></td>
      <td>${s.coordinator_name}</td>
      <td><button class="action-btn btn-danger btn-sm" onclick="deleteSubject(${s.id})">Delete</button></td>
    </tr>
  `).join('');
}

async function addSubject() {
  const name = document.getElementById('subjectName').value.trim();
  const code = document.getElementById('subjectCode').value.trim();
  const coordinator_name = document.getElementById('subjectCoord').value.trim();
  if (!name || !code || !coordinator_name) { showToast('All fields are required.', 'error'); return; }
  try {
    await apiRequest('/admin/subjects', { method: 'POST', body: JSON.stringify({ name, code, coordinator_name }) });
    showToast('Subject added!', 'success');
    document.getElementById('subjectName').value = '';
    document.getElementById('subjectCode').value = '';
    document.getElementById('subjectCoord').value = '';
    await loadSubjects();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function deleteSubject(id) {
  if (!confirm('Delete this subject?')) return;
  try {
    await apiRequest(`/admin/subjects/${id}`, { method: 'DELETE' });
    showToast('Subject deleted.', 'success');
    await loadSubjects();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function loadRooms() {
  try {
    allRooms = await apiRequest('/admin/rooms');
    renderRoomsTable();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderRoomsTable() {
  const tbody = document.getElementById('roomsTable');
  if (!allRooms.length) {
    tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><div class="empty-icon">🏫</div><p>No rooms added yet.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = allRooms.map((r, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${r.room_number}</strong></td>
      <td>${r.capacity} seats</td>
      <td><button class="action-btn btn-danger btn-sm" onclick="deleteRoom(${r.id})">Delete</button></td>
    </tr>
  `).join('');
}

async function addRoom() {
  const room_number = document.getElementById('roomNumber').value.trim();
  const capacity = parseInt(document.getElementById('roomCapacity').value);
  if (!room_number || !capacity || capacity < 1) { showToast('Valid room number and capacity required.', 'error'); return; }
  try {
    await apiRequest('/admin/rooms', { method: 'POST', body: JSON.stringify({ room_number, capacity }) });
    showToast('Room added!', 'success');
    document.getElementById('roomNumber').value = '';
    document.getElementById('roomCapacity').value = '';
    await loadRooms();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function deleteRoom(id) {
  if (!confirm('Delete this room?')) return;
  try {
    await apiRequest(`/admin/rooms/${id}`, { method: 'DELETE' });
    showToast('Room deleted.', 'success');
    await loadRooms();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function populateTimetableSelects() {
  const subjSel = document.getElementById('ttSubject');
  const roomSel = document.getElementById('ttRoom');
  subjSel.innerHTML = '<option value="">Select subject...</option>' + allSubjects.map(s => `<option value="${s.id}">${s.name} (${s.code})</option>`).join('');
  roomSel.innerHTML = '<option value="">Select room...</option>' + allRooms.map(r => `<option value="${r.id}">${r.room_number} (Cap: ${r.capacity})</option>`).join('');
}

async function addTimetableEntry() {
  const subject_id = parseInt(document.getElementById('ttSubject').value);
  const room_id    = parseInt(document.getElementById('ttRoom').value);
  const day_of_week = document.getElementById('ttDay').value;
  const timeSlot   = document.getElementById('ttTimeSlot').value;
  const semester   = document.getElementById('ttSemester').value.trim();
  const section    = document.getElementById('ttSection').value.trim();

  if (!subject_id || !room_id || !day_of_week || !timeSlot || !semester || !section) {
    showToast('All fields are required.', 'error'); return;
  }
  const [start_time, end_time] = timeSlot.split('|');
  try {
    await apiRequest('/admin/timetable', {
      method: 'POST',
      body: JSON.stringify({ subject_id, room_id, day_of_week, start_time, end_time, semester, section })
    });
    showToast('Timetable entry added!', 'success');
    document.getElementById('ttSemester').value = '';
    document.getElementById('ttSection').value  = '';
    loadTimetableEntries();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function loadTimetableEntries() {
  const tbody = document.getElementById('timetableEntriesTable');
  if (!tbody) return;
  try {
    const entries = await apiRequest('/admin/timetable');
    if (!entries.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">📅</div><p>No entries yet.</p></div></td></tr>';
      return;
    }
    tbody.innerHTML = entries.map((e, i) => `
      <tr>
        <td>${i+1}</td>
        <td><strong>${e.subject ? e.subject.code : 'N/A'}</strong><br/><small>${e.subject ? e.subject.name : ''}</small></td>
        <td>${e.room ? e.room.room_number : 'N/A'}</td>
        <td>${e.day_of_week}</td>
        <td>${e.start_time} – ${e.end_time}</td>
        <td>${e.section}</td>
        <td><button class="action-btn btn-danger btn-sm" onclick="deleteTimetableEntry(${e.id})">Delete</button></td>
      </tr>
    `).join('');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:#c62828">${e.message}</td></tr>`;
  }
}

async function renderTimetableGrid() {
  const container = document.getElementById('timetableGrid');
  container.innerHTML = '<div class="loading"><div class="spinner"></div> Loading...</div>';
  try {
    const entries = await apiRequest('/admin/timetable');
    if (!entries.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><p>No timetable entries. Add some first.</p></div>';
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
          const sn = c.subject ? c.subject.name : 'N/A';
          const sc = c.subject ? c.subject.code : '';
          const rm = c.room ? c.room.room_number : 'N/A';
          html += `<div class="tt-entry">
            <strong>${sc}</strong>
            <div style="font-size:0.75rem;color:#37474f">${sn}</div>
            <small>${rm} · ${c.section}</small>
            <div style="margin-top:4px"><button class="action-btn btn-danger btn-sm" onclick="deleteTimetableEntry(${c.id})">×</button></div>
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

async function deleteTimetableEntry(id) {
  if (!confirm('Remove this timetable entry?')) return;
  try {
    await apiRequest(`/admin/timetable/${id}`, { method: 'DELETE' });
    showToast('Entry removed.', 'success');
    renderTimetableGrid();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function downloadTimetablePDF() {
  try {
    const token = getToken();
    const form  = new FormData();
    form.append('college_name',     document.getElementById('pdfCollegeName')?.value    || 'Indian Institute of Information Technology');
    form.append('college_subtitle', document.getElementById('pdfCollegeSubtitle')?.value || '(An Institute of National Importance by an Act of Parliament)');
    form.append('college_address',  document.getElementById('pdfCollegeAddress')?.value  || '');
    form.append('semester_label',   document.getElementById('pdfSemester')?.value        || 'Even Semester, AY 2025-26');
    form.append('section_label',    document.getElementById('pdfSection')?.value         || 'Section B CSE');
    form.append('location_label',   document.getElementById('pdfLocation')?.value        || 'LH8');

    const logoFile = document.getElementById('pdfLogo')?.files[0];
    if (logoFile) form.append('logo', logoFile);

    showToast('Generating PDF…', 'info');
    const res = await fetch('/admin/timetable/pdf', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: form
    });
    if (!res.ok) throw new Error('Failed to generate PDF');
    const blob   = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl; a.download = 'timetable.pdf'; a.click();
    URL.revokeObjectURL(blobUrl);
    showToast('PDF downloaded successfully!', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function generateQuestionBuilders() {
  const count = parseInt(document.getElementById('questionCount').value);
  if (!count || count < 1 || count > 20) { showToast('Enter a number between 1 and 20.', 'error'); return; }
  const container = document.getElementById('questionsBuilderContainer');
  container.innerHTML = '';
  for (let i = 1; i <= count; i++) {
    const div = document.createElement('div');
    div.className = 'card question-builder';
    div.innerHTML = `
      <div class="question-builder-header">
        <span class="question-num">Question ${i}</span>
      </div>
      <div class="form-row">
        <div class="field-group" style="grid-column:1/-1">
          <label>Question Text</label>
          <input type="text" id="qText_${i}" placeholder="Enter your question..." />
        </div>
        <div class="field-group">
          <label>Question Type</label>
          <select id="qType_${i}" onchange="handleQuestionTypeChange(${i})">
            <option value="rating">Rating (1–5)</option>
            <option value="text">Text Response</option>
            <option value="mcq">Multiple Choice</option>
          </select>
        </div>
      </div>
      <div class="options-container" id="qOptions_${i}"></div>
    `;
    container.appendChild(div);
  }
  document.getElementById('submitFeedbackFormBtn').style.display = 'block';
}

function handleQuestionTypeChange(idx) {
  const type = document.getElementById(`qType_${idx}`).value;
  const container = document.getElementById(`qOptions_${idx}`);
  if (type === 'mcq') {
    container.innerHTML = `
      <label style="font-size:0.8rem;font-weight:600;color:#546e7a;margin-bottom:0.5rem;display:block">MCQ Options</label>
      <div id="mcqRows_${idx}">
        <div class="option-row"><input type="text" placeholder="Option 1" id="mcqOpt_${idx}_1" /><button class="action-btn btn-outline btn-sm" onclick="addMCQOption(${idx})">+ Add</button></div>
      </div>
    `;
  } else {
    container.innerHTML = '';
  }
}

let mcqCounts = {};
function addMCQOption(idx) {
  mcqCounts[idx] = (mcqCounts[idx] || 1) + 1;
  const n = mcqCounts[idx];
  const row = document.createElement('div');
  row.className = 'option-row';
  row.innerHTML = `<input type="text" placeholder="Option ${n}" id="mcqOpt_${idx}_${n}" />
    <button class="action-btn btn-danger btn-sm" onclick="this.parentElement.remove()">×</button>`;
  document.getElementById(`mcqRows_${idx}`).appendChild(row);
}

async function submitFeedbackForm() {
  const title = document.getElementById('formTitle').value.trim();
  const count = parseInt(document.getElementById('questionCount').value);
  if (!title) { showToast('Form title is required.', 'error'); return; }
  const questions = [];
  for (let i = 1; i <= count; i++) {
    const question_text = document.getElementById(`qText_${i}`)?.value.trim();
    const question_type = document.getElementById(`qType_${i}`)?.value;
    if (!question_text) { showToast(`Question ${i} text is required.`, 'error'); return; }
    let options = null;
    if (question_type === 'mcq') {
      const optInputs = document.querySelectorAll(`[id^="mcqOpt_${i}_"]`);
      options = Array.from(optInputs).map(inp => inp.value.trim()).filter(v => v);
      if (options.length < 2) { showToast(`Question ${i} needs at least 2 MCQ options.`, 'error'); return; }
    }
    questions.push({ question_text, question_type, options });
  }
  try {
    await apiRequest('/admin/feedback/form', { method: 'POST', body: JSON.stringify({ title, questions }) });
    showToast('Feedback form created!', 'success');
    document.getElementById('formTitle').value = '';
    document.getElementById('questionCount').value = '';
    document.getElementById('questionsBuilderContainer').innerHTML = '';
    document.getElementById('submitFeedbackFormBtn').style.display = 'none';
    await loadForms();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function loadForms() {
  try {
    allForms = await apiRequest('/admin/feedback/forms');
  } catch (e) {
    allForms = [];
  }
}

function populateShareFormSelect() {
  const sel = document.getElementById('shareFormSelect');
  sel.innerHTML = '<option value="">Select form...</option>' + allForms.map(f => `<option value="${f.id}">${f.title}</option>`).join('');
}

function populateResponseFormSelect() {
  const sel = document.getElementById('responseFormSelect');
  sel.innerHTML = '<option value="">Select form...</option>' + allForms.map(f => `<option value="${f.id}">${f.title}</option>`).join('');
}

async function loadStudents() {
  try {
    allStudents = await apiRequest('/admin/feedback/students');
    renderStudentChecklist();
  } catch (e) {
    allStudents = [];
  }
}

function renderStudentChecklist() {
  const container = document.getElementById('studentChecklist');
  if (!allStudents.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎓</div><p>No students registered yet.</p></div>';
    return;
  }
  container.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.6rem">
    ${allStudents.map(s => `
      <label style="display:flex;align-items:center;gap:0.6rem;padding:0.65rem 0.9rem;border:1.5px solid #e8eaf6;border-radius:8px;cursor:pointer;font-size:0.88rem;transition:all 0.2s"
        onmouseover="this.style.borderColor='#5c6bc0'" onmouseout="this.style.borderColor='#e8eaf6'">
        <input type="checkbox" value="${s.id}" style="accent-color:#1a237e" />
        <div>
          <div style="font-weight:600;color:#263238">${s.username}</div>
          <div style="font-size:0.75rem;color:#90a4ae">${s.email}</div>
        </div>
      </label>
    `).join('')}
  </div>`;
}

async function shareForm() {
  const form_id = document.getElementById('shareFormSelect').value;
  if (!form_id) { showToast('Select a form first.', 'error'); return; }
  const checked = document.querySelectorAll('#studentChecklist input[type=checkbox]:checked');
  const student_ids = Array.from(checked).map(c => parseInt(c.value));
  if (!student_ids.length) { showToast('Select at least one student.', 'error'); return; }
  try {
    const res = await apiRequest(`/admin/feedback/form/${form_id}/share`, { method: 'POST', body: JSON.stringify({ student_ids }) });
    showToast(res.message, 'success');
    document.querySelectorAll('#studentChecklist input[type=checkbox]').forEach(c => c.checked = false);
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function loadResponses() {
  const form_id = document.getElementById('responseFormSelect').value;
  const container = document.getElementById('responsesContainer');
  if (!form_id) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><p>Select a form to view responses.</p></div>';
    return;
  }
  container.innerHTML = '<div class="loading"><div class="spinner"></div> Loading responses...</div>';
  try {
    const responses = await apiRequest(`/admin/feedback/responses/${form_id}`);
    if (!responses.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>No responses submitted yet.</p></div>';
      return;
    }
    const byStudent = {};
    responses.forEach(r => {
      if (!byStudent[r.student_username]) byStudent[r.student_username] = [];
      byStudent[r.student_username].push(r);
    });
    let html = '';
    Object.entries(byStudent).forEach(([student, resps]) => {
      html += `<div style="margin-bottom:1.5rem">
        <div style="font-weight:700;color:#1a237e;font-size:0.95rem;margin-bottom:0.75rem;padding-bottom:0.5rem;border-bottom:1.5px solid #e8eaf6">
          🎓 ${student}
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Question</th><th>Answer</th><th>Submitted At</th></tr></thead>
            <tbody>
              ${resps.map((r, i) => `
                <tr>
                  <td>${i + 1}</td>
                  <td>${r.question_text}</td>
                  <td><strong>${r.answer}</strong></td>
                  <td style="color:#90a4ae;font-size:0.8rem">${formatDate(r.submitted_at)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>`;
    });
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p style="color:#c62828">${e.message}</p></div>`;
  }
}


function populateResetPasswordSection() {
  const sel = document.getElementById('resetStudentSelect');
  sel.innerHTML = '<option value="">Select student...</option>' +
    allStudents.map(s => `<option value="${s.id}">${s.username} — ${s.email}</option>`).join('');
  renderStudentsListTable();
}

function renderStudentsListTable() {
  const tbody = document.getElementById('studentsListTable');
  if (!allStudents.length) {
    tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><div class="empty-icon">🎓</div><p>No students registered yet.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = allStudents.map((s, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${s.username}</strong></td>
      <td>${s.email}</td>
      <td>
        <button class="action-btn btn-orange btn-sm" onclick="quickReset(${s.id}, '${s.username}')">
          🔑 Reset
        </button>
      </td>
    </tr>
  `).join('');
}

async function quickReset(studentId, username) {
  const newPassword = prompt(`Enter new password for "${username}" (min 6 characters):`);
  if (!newPassword) return;
  if (newPassword.length < 6) {
    showToast('Password must be at least 6 characters.', 'error');
    return;
  }
  try {
    const res = await apiRequest('/admin/reset-student-password', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId, new_password: newPassword })
    });
    showToast(`Password reset for "${username}". New password: ${newPassword}`, 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function resetStudentPassword() {
  const studentId = parseInt(document.getElementById('resetStudentSelect').value);
  const newPassword = document.getElementById('resetNewPassword').value.trim();
  const confirmPassword = document.getElementById('resetConfirmPassword').value.trim();

  if (!studentId) { showToast('Please select a student.', 'error'); return; }
  if (!newPassword) { showToast('Please enter a new password.', 'error'); return; }
  if (newPassword.length < 6) { showToast('Password must be at least 6 characters.', 'error'); return; }
  if (newPassword !== confirmPassword) { showToast('Passwords do not match.', 'error'); return; }

  try {
    await apiRequest('/admin/reset-student-password', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId, new_password: newPassword })
    });
    const student = allStudents.find(s => s.id === studentId);
    showToast(`Password reset successfully for "${student?.username}".`, 'success');
    document.getElementById('resetStudentSelect').value = '';
    document.getElementById('resetNewPassword').value = '';
    document.getElementById('resetConfirmPassword').value = '';
  } catch (e) {
    showToast(e.message, 'error');
  }
}