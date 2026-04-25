requireAuth('admin');

let allSubjects = [];
let allRooms = [];
let allForms = [];
let allStudents = [];
let allTeachers = [];
let editingTeacherId = null;

const ALL_DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const ALL_SLOTS = [
  '09:30|10:30','10:30|11:30','11:30|12:30',
  '13:30|14:30','14:30|15:30','15:30|16:30','16:30|17:30'
];

document.addEventListener('DOMContentLoaded', () => {
  const username = getUsername();
  document.getElementById('sidebarUsername').textContent = username || 'Admin';
  document.getElementById('userAvatar').textContent = (username || 'A')[0].toUpperCase();
  document.getElementById('topbarDate').textContent = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  loadSubjects();
  loadRooms();
  loadTeachers();
  loadForms();
  loadStudents();

  // Lab duration toggle
  const labSelect = document.getElementById('subjectIsLab');
  if (labSelect) {
    labSelect.addEventListener('change', () => {
      document.getElementById('labDurationGroup').style.display =
        labSelect.value === 'true' ? 'block' : 'none';
    });
  }
});

function showSection(name, el) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.getElementById(`section-${name}`).classList.add('active');
  if (el) el.classList.add('active');
  const titles = {
    'subjects': 'Manage Subjects', 'teachers': 'Manage Teachers',
    'rooms': 'Manage Rooms', 'timetable': 'Build Timetable',
    'auto-generate': 'Auto-Generate Timetable',
    'view-timetable': 'View Timetable', 'create-feedback': 'Create Feedback Form',
    'share-feedback': 'Share Feedback', 'view-responses': 'View Responses',
    'reset-password': 'Reset Student Password'
  };
  document.getElementById('topbarTitle').textContent = titles[name] || name;
  if (name === 'view-timetable') renderTimetableGrid();
  if (name === 'timetable') { populateTimetableSelects(); loadTimetableEntries(); }
  if (name === 'auto-generate') { populateAutoGenSubjects(); }
  if (name === 'share-feedback') populateShareFormSelect();
  if (name === 'view-responses') populateResponseFormSelect();
  if (name === 'reset-password') populateResetPasswordSection();
  if (name === 'subjects') populateSubjectTeacherSelect();

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


// ═══════════════════════════════════════════════════════════════════════
//  TEACHERS
// ═══════════════════════════════════════════════════════════════════════
async function loadTeachers() {
  try {
    allTeachers = await apiRequest('/admin/teachers');
    renderTeachersTable();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderTeachersTable() {
  const tbody = document.getElementById('teachersTable');
  if (!tbody) return;
  if (!allTeachers.length) {
    tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">👨‍🏫</div><p>No teachers added yet.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = allTeachers.map((t, i) => {
    const unavailCount = (t.unavailable_slots || []).length;
    const unavailBadge = unavailCount > 0
      ? `<span class="badge badge-warn">${unavailCount} blocked</span>`
      : '<span class="badge badge-ok">Fully available</span>';
    return `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${t.name}</strong></td>
      <td>${t.email || '<span style="color:#90a4ae">—</span>'}</td>
      <td>${unavailBadge}</td>
      <td>
        <button class="action-btn btn-orange btn-sm" onclick="openAvailabilityModal(${t.id})">⏰ Availability</button>
        <button class="action-btn btn-danger btn-sm" onclick="deleteTeacher(${t.id})">Delete</button>
      </td>
    </tr>
  `}).join('');
}

async function addTeacher() {
  const name = document.getElementById('teacherName').value.trim();
  const email = document.getElementById('teacherEmail').value.trim() || null;
  if (!name) { showToast('Teacher name is required.', 'error'); return; }
  try {
    await apiRequest('/admin/teachers', {
      method: 'POST',
      body: JSON.stringify({ name, email, unavailable_slots: [] })
    });
    showToast('Teacher added!', 'success');
    document.getElementById('teacherName').value = '';
    document.getElementById('teacherEmail').value = '';
    await loadTeachers();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function deleteTeacher(id) {
  if (!confirm('Delete this teacher? Their subject assignments will be cleared.')) return;
  try {
    await apiRequest(`/admin/teachers/${id}`, { method: 'DELETE' });
    showToast('Teacher deleted.', 'success');
    await loadTeachers();
    await loadSubjects();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function openAvailabilityModal(teacherId) {
  const teacher = allTeachers.find(t => t.id === teacherId);
  if (!teacher) return;
  editingTeacherId = teacherId;
  document.getElementById('availTeacherName').textContent = teacher.name;

  const unavail = new Set((teacher.unavailable_slots || []).map(s => `${s.day}|${s.slot}`));

  const grid = document.getElementById('availGrid');
  let html = '<thead><tr><th></th>';
  ALL_DAYS.forEach(d => { html += `<th>${d.substring(0, 3)}</th>`; });
  html += '</tr></thead><tbody>';

  ALL_SLOTS.forEach(slot => {
    const [st, et] = slot.split('|');
    html += `<tr><td class="avail-time">${st}–${et}</td>`;
    ALL_DAYS.forEach(day => {
      const key = `${day}|${slot}`;
      const isBlocked = unavail.has(key);
      html += `<td class="avail-cell ${isBlocked ? 'blocked' : ''}"
                   data-key="${key}" onclick="toggleAvailCell(this)"></td>`;
    });
    html += '</tr>';
  });
  html += '</tbody>';
  grid.innerHTML = html;

  document.getElementById('availabilityModal').style.display = 'flex';
}

function closeAvailabilityModal() {
  document.getElementById('availabilityModal').style.display = 'none';
  editingTeacherId = null;
}

function toggleAvailCell(cell) {
  cell.classList.toggle('blocked');
}

async function saveAvailability() {
  if (!editingTeacherId) return;
  const cells = document.querySelectorAll('#availGrid .avail-cell.blocked');
  const unavailable_slots = Array.from(cells).map(cell => {
    const [day, slot] = cell.dataset.key.split('|', 1).concat(cell.dataset.key.substring(cell.dataset.key.indexOf('|') + 1));
    return { day, slot };
  });

  try {
    await apiRequest(`/admin/teachers/${editingTeacherId}`, {
      method: 'PUT',
      body: JSON.stringify({ unavailable_slots })
    });
    showToast('Availability saved!', 'success');
    closeAvailabilityModal();
    await loadTeachers();
  } catch (e) {
    showToast(e.message, 'error');
  }
}


// ═══════════════════════════════════════════════════════════════════════
//  SUBJECTS
// ═══════════════════════════════════════════════════════════════════════
async function loadSubjects() {
  try {
    allSubjects = await apiRequest('/admin/subjects');
    renderSubjectsTable();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function populateSubjectTeacherSelect() {
  const sel = document.getElementById('subjectTeacher');
  if (!sel) return;
  sel.innerHTML = '<option value="">No teacher assigned</option>' +
    allTeachers.map(t => `<option value="${t.id}">${t.name}${t.email ? ' ('+t.email+')' : ''}</option>`).join('');
}

function renderSubjectsTable() {
  const tbody = document.getElementById('subjectsTable');
  if (!allSubjects.length) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-icon">📚</div><p>No subjects added yet.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = allSubjects.map((s, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${s.name}</strong></td>
      <td><code>${s.code}</code></td>
      <td>${s.coordinator_name}</td>
      <td>${s.teacher ? `<span class="badge badge-ok">${s.teacher.name}</span>` : '<span style="color:#90a4ae">—</span>'}</td>
      <td>${s.lectures_per_week}</td>
      <td>${s.is_lab ? '<span class="badge badge-lab">Lab</span>' : '<span class="badge badge-theory">Theory</span>'}</td>
      <td><button class="action-btn btn-danger btn-sm" onclick="deleteSubject(${s.id})">Delete</button></td>
    </tr>
  `).join('');
}

async function addSubject() {
  const name = document.getElementById('subjectName').value.trim();
  const code = document.getElementById('subjectCode').value.trim();
  const coordinator_name = document.getElementById('subjectCoord').value.trim();
  const teacher_id = parseInt(document.getElementById('subjectTeacher').value) || null;
  const lectures_per_week = parseInt(document.getElementById('subjectLPW').value) || 3;
  const is_lab = document.getElementById('subjectIsLab').value === 'true';
  const lab_duration = parseInt(document.getElementById('subjectLabDuration').value) || 2;

  if (!name || !code || !coordinator_name) { showToast('Name, code, and coordinator are required.', 'error'); return; }
  try {
    await apiRequest('/admin/subjects', {
      method: 'POST',
      body: JSON.stringify({ name, code, coordinator_name, teacher_id, lectures_per_week, is_lab, lab_duration })
    });
    showToast('Subject added!', 'success');
    document.getElementById('subjectName').value = '';
    document.getElementById('subjectCode').value = '';
    document.getElementById('subjectCoord').value = '';
    document.getElementById('subjectTeacher').value = '';
    document.getElementById('subjectLPW').value = '3';
    document.getElementById('subjectIsLab').value = 'false';
    document.getElementById('subjectLabDuration').value = '2';
    document.getElementById('labDurationGroup').style.display = 'none';
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


// ═══════════════════════════════════════════════════════════════════════
//  ROOMS
// ═══════════════════════════════════════════════════════════════════════
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


// ═══════════════════════════════════════════════════════════════════════
//  TIMETABLE (Manual)
// ═══════════════════════════════════════════════════════════════════════
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
    container.innerHTML = buildTimetableHTML(entries, true);
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p style="color:#c62828">${e.message}</p></div>`;
  }
}

function buildTimetableHTML(entries, showDelete = false) {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const daysPresent = days.filter(d => entries.some(e => e.day_of_week === d));
  const timeSlots = [...new Set(entries.map(e => `${e.start_time}|${e.end_time}`))].sort();
  const entryMap = {};
  entries.forEach(e => {
    const key = `${e.day_of_week}|${e.start_time}|${e.end_time}`;
    if (!entryMap[key]) entryMap[key] = [];
    entryMap[key].push(e);
  });

  const subjectColors = {};
  const colorPalette = [
    '#fff59d','#a5d6a7','#ef9a9a','#b3e5fc','#ce93d8',
    '#80cbc4','#ffcc80','#f48fb1','#bcaaa4','#b0bec5',
    '#c5cae9','#dcedc8','#ffe0b2','#f8bbd0','#b2dfdb'
  ];
  let colorIdx = 0;
  entries.forEach(e => {
    const code = e.subject_code || (e.subject ? e.subject.code : 'N/A');
    if (!subjectColors[code]) {
      subjectColors[code] = colorPalette[colorIdx % colorPalette.length];
      colorIdx++;
    }
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
        const sn = c.subject_name || (c.subject ? c.subject.name : 'N/A');
        const sc = c.subject_code || (c.subject ? c.subject.code : '');
        const rm = c.room_number || (c.room ? c.room.room_number : 'N/A');
        const tn = c.teacher_name || '';
        const bg = subjectColors[sc] || '#e3f2fd';
        html += `<div class="tt-entry" style="background:${bg}">
          <strong>${sc}</strong>
          <div style="font-size:0.75rem;color:#37474f">${sn}</div>
          <small>${rm}${tn ? ' · ' + tn : ''}</small>`;
        if (showDelete && c.id) {
          html += `<div style="margin-top:4px"><button class="action-btn btn-danger btn-sm" onclick="deleteTimetableEntry(${c.id})">×</button></div>`;
        }
        html += '</div>';
      });
      html += '</td>';
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
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


// ═══════════════════════════════════════════════════════════════════════
//  AUTO-GENERATE TIMETABLE
// ═══════════════════════════════════════════════════════════════════════
function populateAutoGenSubjects() {
  const container = document.getElementById('agSubjectsList');
  if (!allSubjects.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📚</div><p>No subjects. Add subjects first.</p></div>';
    return;
  }
  container.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:0.6rem">
    ${allSubjects.map(s => `
      <label class="ag-subject-card">
        <input type="checkbox" value="${s.id}" checked />
        <div class="ag-subject-info">
          <div class="ag-subject-name">${s.name} <code>${s.code}</code></div>
          <div class="ag-subject-meta">
            ${s.is_lab ? '<span class="badge badge-lab">Lab</span>' : '<span class="badge badge-theory">Theory</span>'}
            <span>${s.lectures_per_week} lec/wk</span>
            ${s.teacher ? `<span>👨‍🏫 ${s.teacher.name}</span>` : ''}
          </div>
        </div>
      </label>
    `).join('')}
  </div>`;
}

function refreshAutoGenSummary() {
  const semester = document.getElementById('agSemester').value.trim();
  const section = document.getElementById('agSection').value.trim();
  const dayCheckboxes = document.querySelectorAll('.day-checkboxes input:checked');
  const days = Array.from(dayCheckboxes).map(c => c.value);
  const subjectCheckboxes = document.querySelectorAll('#agSubjectsList input:checked');
  const selectedSubjectIds = Array.from(subjectCheckboxes).map(c => parseInt(c.value));
  const selectedSubjects = allSubjects.filter(s => selectedSubjectIds.includes(s.id));

  const container = document.getElementById('agSummary');

  if (!semester || !section) {
    container.innerHTML = '<p style="color:#ff5722">⚠️ Please fill in semester and section.</p>';
    return;
  }

  let totalSlots = 0;
  selectedSubjects.forEach(s => {
    if (s.is_lab) {
      totalSlots += s.lectures_per_week * (s.lab_duration || 2);
    } else {
      totalSlots += s.lectures_per_week;
    }
  });

  const availableSlots = days.length * ALL_SLOTS.length;
  const utilizationPct = availableSlots > 0 ? Math.round((totalSlots / availableSlots) * 100) : 0;
  const isOverCapacity = totalSlots > availableSlots;

  container.innerHTML = `
    <div class="ag-summary-grid">
      <div class="ag-stat">
        <div class="ag-stat-value">${selectedSubjects.length}</div>
        <div class="ag-stat-label">Subjects</div>
      </div>
      <div class="ag-stat">
        <div class="ag-stat-value">${allRooms.length}</div>
        <div class="ag-stat-label">Rooms</div>
      </div>
      <div class="ag-stat">
        <div class="ag-stat-value">${days.length}</div>
        <div class="ag-stat-label">Days</div>
      </div>
      <div class="ag-stat">
        <div class="ag-stat-value">${totalSlots}</div>
        <div class="ag-stat-label">Slots Needed</div>
      </div>
      <div class="ag-stat">
        <div class="ag-stat-value">${availableSlots}</div>
        <div class="ag-stat-label">Slots Available</div>
      </div>
      <div class="ag-stat ${isOverCapacity ? 'ag-stat-warn' : 'ag-stat-ok'}">
        <div class="ag-stat-value">${utilizationPct}%</div>
        <div class="ag-stat-label">Utilization</div>
      </div>
    </div>
    ${isOverCapacity ? '<p style="color:#ff5722;margin-top:0.8rem">⚠️ More slots needed than available. Some subjects may not be fully placed.</p>' : ''}
    <div style="margin-top:0.8rem;font-size:0.85rem;color:var(--text-secondary)">
      <strong>Semester:</strong> ${semester} · <strong>Section:</strong> ${section} · <strong>Days:</strong> ${days.map(d => d.substring(0,3)).join(', ')}
    </div>
  `;
}

async function runAutoGenerate() {
  const semester = document.getElementById('agSemester').value.trim();
  const section = document.getElementById('agSection').value.trim();
  const dayCheckboxes = document.querySelectorAll('.day-checkboxes input:checked');
  const days = Array.from(dayCheckboxes).map(c => c.value);
  const subjectCheckboxes = document.querySelectorAll('#agSubjectsList input:checked');
  const subject_ids = Array.from(subjectCheckboxes).map(c => parseInt(c.value));

  if (!semester || !section) { showToast('Semester and section are required.', 'error'); return; }
  if (days.length === 0) { showToast('Select at least one day.', 'error'); return; }
  if (subject_ids.length === 0) { showToast('Select at least one subject.', 'error'); return; }

  // Show loading state
  const resultArea = document.getElementById('agResultArea');
  const resultCard = document.getElementById('agResultCard');
  const resultTitle = document.getElementById('agResultTitle');
  const warningsDiv = document.getElementById('agWarnings');
  const resultGrid = document.getElementById('agResultGrid');
  const resultStats = document.getElementById('agResultStats');

  resultArea.style.display = 'block';
  resultTitle.innerHTML = '⏳ Generating...';
  resultGrid.innerHTML = '<div class="loading"><div class="spinner"></div> Running scheduling algorithm...</div>';
  warningsDiv.innerHTML = '';
  resultStats.innerHTML = '';
  resultCard.className = 'card';

  try {
    const result = await apiRequest('/admin/timetable/auto-generate', {
      method: 'POST',
      body: JSON.stringify({ semester, section, days, subject_ids })
    });

    if (result.success && result.entries.length > 0) {
      resultTitle.innerHTML = '🎉 Timetable Generated Successfully!';
      resultCard.classList.add('ag-success');

      // Show warnings
      if (result.warnings && result.warnings.length > 0) {
        warningsDiv.innerHTML = result.warnings.map(w =>
          `<div class="ag-warning">⚠️ ${w}</div>`
        ).join('');
      }

      // Build timetable grid from generated entries
      const gridEntries = result.entries.map(e => ({
        day_of_week: e.day_of_week,
        start_time: e.start_time,
        end_time: e.end_time,
        subject_code: e.subject_code,
        subject_name: e.subject_name,
        room_number: e.room_number,
        teacher_name: e.teacher_name,
      }));
      resultGrid.innerHTML = buildTimetableHTML(gridEntries, false);

      // Stats
      resultStats.innerHTML = `
        <div class="ag-result-stats">
          <span class="ag-result-stat">✅ <strong>${result.total_placed}</strong> entries placed</span>
          <span class="ag-result-stat">📊 <strong>${result.total_required}</strong> slots required</span>
        </div>
      `;

      showToast('Timetable generated and saved successfully!', 'success');
    } else {
      resultTitle.innerHTML = '❌ Generation Failed';
      resultCard.classList.add('ag-failure');
      resultGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">😔</div><p>Could not generate a valid timetable.</p></div>';
      if (result.warnings) {
        warningsDiv.innerHTML = result.warnings.map(w =>
          `<div class="ag-warning">⚠️ ${w}</div>`
        ).join('');
      }
    }
  } catch (e) {
    resultTitle.innerHTML = '❌ Error';
    resultCard.classList.add('ag-failure');
    resultGrid.innerHTML = `<div class="empty-state"><p style="color:#c62828">${e.message}</p></div>`;
    showToast(e.message, 'error');
  }
}


// ═══════════════════════════════════════════════════════════════════════
//  FEEDBACK & STUDENT PASSWORD (unchanged logic)
// ═══════════════════════════════════════════════════════════════════════
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