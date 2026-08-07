import React, { useState, useEffect } from 'react';
import { 
  Upload, Plus, Trash2, Check, FileText, Briefcase, FolderGit2, 
  Loader2, Target, Edit2, Award, X, ExternalLink, 
  Layers, Save
} from 'lucide-react';
import { api } from '../api';
import { SkeletonCard } from './Skeleton';

interface ResumeContextViewProps {
  onLoadingChange?: (loading: boolean) => void;
}

export const ResumeContextView: React.FC<ResumeContextViewProps> = ({ onLoadingChange }) => {
  const [resumes, setResumes] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>({});
  const [jobPref, setJobPref] = useState<any>({
    role_1: '', role_2: '', role_3: '',
    min_lpa: '', max_lpa: '', locations: '', experience_level: 'fresher'
  });
  const [experiences, setExperiences] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingJobPref, setSavingJobPref] = useState(false);
  const [addingExp, setAddingExp] = useState(false);
  const [addingProj, setAddingProj] = useState(false);
  const [addingAch, setAddingAch] = useState(false);
  const [showAddExp, setShowAddExp] = useState(false);
  const [showAddProj, setShowAddProj] = useState(false);
  const [showAddAch, setShowAddAch] = useState(false);

  const [msg, setMsg] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [parseMode, setParseMode] = useState<string>('keep_unique');

  // New Item States
  const [newExp, setNewExp] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '' });
  const [newProj, setNewProj] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '', link: '' });
  const [newAchText, setNewAchText] = useState('');

  // Editing States
  const [editingExpId, setEditingExpId] = useState<number | null>(null);
  const [editExpForm, setEditExpForm] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '' });
  const [savingExpId, setSavingExpId] = useState<number | null>(null);

  const [editingProjId, setEditingProjId] = useState<number | null>(null);
  const [editProjForm, setEditProjForm] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '', link: '' });
  const [savingProjId, setSavingProjId] = useState<number | null>(null);

  const [editingAchId, setEditingAchId] = useState<number | null>(null);
  const [editAchText, setEditAchText] = useState('');
  const [savingAchId, setSavingAchId] = useState<number | null>(null);

  const loadData = async () => {
    onLoadingChange?.(true);
    try {
      const [resList, profData, prefData, expList, projList, achList] = await Promise.all([
        api.listResumes(),
        api.getProfile(),
        api.getJobPreferences(),
        api.listExperiences(),
        api.listProjects(),
        api.listAchievements(),
      ]);
      setResumes(resList);
      setProfile(profData);
      setJobPref(prefData || {});
      setExperiences(expList);
      setProjects(projList);
      setAchievements(achList);
    } catch (e: any) {
      console.error(e);
    } finally {
      setInitialLoading(false);
      onLoadingChange?.(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    onLoadingChange?.(true);
    setMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.uploadResume(formData, parseMode);
      setMsg(`Resume uploaded & parsed! AI extracted experience, projects, and achievements.`);
      setFile(null);
      await loadData();
    } catch (err: any) {
      setMsg('Upload error: ' + err.message);
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  };

  const handleDeleteResume = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this resume? This action cannot be undone.")) {
      return;
    }
    try {
      await api.deleteResume(id);
      setMsg('Resume deleted successfully.');
      await loadData();
    } catch (err: any) {
      setMsg('Error deleting resume: ' + err.message);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await api.updateProfile(profile);
      setMsg('Profile updated successfully!');
    } catch (err: any) {
      setMsg('Error updating profile: ' + err.message);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleUpdateJobPref = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingJobPref(true);
    try {
      await api.updateJobPreferences({
        ...jobPref,
        min_lpa: jobPref.min_lpa ? parseFloat(jobPref.min_lpa) : null,
        max_lpa: jobPref.max_lpa ? parseFloat(jobPref.max_lpa) : null,
      });
      setMsg('Target Job Preferences updated successfully! Active for Auto-Discover search.');
    } catch (err: any) {
      setMsg('Error updating job preferences: ' + err.message);
    } finally {
      setSavingJobPref(false);
    }
  };

  // --- Experience Actions ---
  const handleAddExperience = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingExp(true);
    try {
      await api.createExperience({
        ...newExp,
        stack: newExp.stack ? newExp.stack.split(',').map((s) => s.trim()) : [],
        tags: newExp.tags ? newExp.tags.split(',').map((t) => t.trim()) : [],
      });
      setNewExp({ title: '', dates: '', one_liner: '', stack: '', tags: '' });
      setShowAddExp(false);
      setMsg('Experience entry added!');
      await loadData();
    } catch (err: any) {
      setMsg('Error adding experience: ' + err.message);
    } finally {
      setAddingExp(false);
    }
  };

  const startEditExperience = (exp: any) => {
    setEditingExpId(exp.id);
    setEditExpForm({
      title: exp.title || '',
      dates: exp.dates || '',
      one_liner: exp.one_liner || '',
      stack: exp.stack ? exp.stack.join(', ') : '',
      tags: exp.tags ? exp.tags.join(', ') : '',
    });
  };

  const handleSaveExperience = async (e: React.FormEvent, id: number) => {
    e.preventDefault();
    setSavingExpId(id);
    try {
      await api.updateExperience(id, {
        ...editExpForm,
        stack: editExpForm.stack ? editExpForm.stack.split(',').map((s) => s.trim()) : [],
        tags: editExpForm.tags ? editExpForm.tags.split(',').map((t) => t.trim()) : [],
      });
      setEditingExpId(null);
      setMsg('Experience entry updated successfully!');
      await loadData();
    } catch (err: any) {
      setMsg('Error updating experience: ' + err.message);
    } finally {
      setSavingExpId(null);
    }
  };

  // --- Project Actions ---
  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingProj(true);
    try {
      await api.createProject({
        ...newProj,
        stack: newProj.stack ? newProj.stack.split(',').map((s) => s.trim()) : [],
        tags: newProj.tags ? newProj.tags.split(',').map((t) => t.trim()) : [],
      });
      setNewProj({ title: '', dates: '', one_liner: '', stack: '', tags: '', link: '' });
      setShowAddProj(false);
      setMsg('Project entry added!');
      await loadData();
    } catch (err: any) {
      setMsg('Error adding project: ' + err.message);
    } finally {
      setAddingProj(false);
    }
  };

  const startEditProject = (proj: any) => {
    setEditingProjId(proj.id);
    setEditProjForm({
      title: proj.title || '',
      dates: proj.dates || '',
      one_liner: proj.one_liner || '',
      stack: proj.stack ? proj.stack.join(', ') : '',
      tags: proj.tags ? proj.tags.join(', ') : '',
      link: proj.link || '',
    });
  };

  const handleSaveProject = async (e: React.FormEvent, id: number) => {
    e.preventDefault();
    setSavingProjId(id);
    try {
      await api.updateProject(id, {
        ...editProjForm,
        stack: editProjForm.stack ? editProjForm.stack.split(',').map((s) => s.trim()) : [],
        tags: editProjForm.tags ? editProjForm.tags.split(',').map((t) => t.trim()) : [],
      });
      setEditingProjId(null);
      setMsg('Project entry updated successfully!');
      await loadData();
    } catch (err: any) {
      setMsg('Error updating project: ' + err.message);
    } finally {
      setSavingProjId(null);
    }
  };

  // --- Achievement Actions ---
  const handleAddAchievement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAchText) return;
    setAddingAch(true);
    try {
      await api.createAchievement({ text: newAchText });
      setNewAchText('');
      setShowAddAch(false);
      setMsg('Achievement added successfully!');
      await loadData();
    } catch (err: any) {
      setMsg('Error adding achievement: ' + err.message);
    } finally {
      setAddingAch(false);
    }
  };

  const startEditAchievement = (ach: any) => {
    setEditingAchId(ach.id);
    setEditAchText(ach.text || '');
  };

  const handleSaveAchievement = async (e: React.FormEvent, id: number) => {
    e.preventDefault();
    setSavingAchId(id);
    try {
      await api.updateAchievement(id, { text: editAchText });
      setEditingAchId(null);
      setMsg('Achievement updated successfully!');
      await loadData();
    } catch (err: any) {
      setMsg('Error updating achievement: ' + err.message);
    } finally {
      setSavingAchId(null);
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={26} color="var(--primary)" /> Context Engine & AI Knowledge Base
          </h1>
          <p className="page-subtitle">
            Upload resumes to auto-extract experience or fine-tune and edit your AI knowledge entries with full control.
          </p>
        </div>
      </div>

      {/* Quick Summary Metrics Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        <div style={{ padding: '14px 18px', background: 'var(--surface-container-lowest)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Resumes</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>{resumes.length}</div>
        </div>
        <div style={{ padding: '14px 18px', background: 'var(--surface-container-lowest)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Experiences</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>{experiences.length}</div>
        </div>
        <div style={{ padding: '14px 18px', background: 'var(--surface-container-lowest)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Projects</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>{projects.length}</div>
        </div>
        <div style={{ padding: '14px 18px', background: 'var(--surface-container-lowest)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Achievements</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>{achievements.length}</div>
        </div>
      </div>

      {msg && (
        <div className="alert alert-info" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', borderRadius: '8px' }}>
          <span>{msg}</span>
          <button className="btn btn-secondary btn-sm" onClick={() => setMsg('')} style={{ padding: '2px 6px', border: 'none' }}><X size={14} /></button>
        </div>
      )}

      {/* Resume Upload Card */}
      <div className="card" style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.03)', borderRadius: '12px' }}>
        <div className="card-header" style={{ marginBottom: '14px' }}>
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '17px', fontWeight: 600 }}>
            <FileText size={18} color="var(--primary)" /> Resume Parser (LLM Auto-Extraction)
          </h3>
          <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '12px', background: 'rgba(37, 99, 235, 0.1)', color: 'var(--primary)', fontWeight: 600 }}>
            AI-Powered
          </span>
        </div>
        <form onSubmit={handleUploadResume}>
          <div className="form-group" style={{ marginBottom: '14px' }}>
            <label className="form-label" style={{ fontSize: '13px', fontWeight: 600 }}>Parsing Strategy</label>
            <div style={{ display: 'flex', gap: '20px', fontSize: '13px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="parseMode"
                  value="keep_unique"
                  checked={parseMode === 'keep_unique'}
                  onChange={() => setParseMode('keep_unique')}
                />
                <span><strong>Keep Existing</strong> & append unique items</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="parseMode"
                  value="replace"
                  checked={parseMode === 'replace'}
                  onChange={() => setParseMode('replace')}
                />
                <span style={{ color: 'var(--error)' }}><strong>Replace All</strong> with new resume</span>
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="file"
              accept=".pdf,.txt,.doc,.docx"
              className="form-input"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              required
              style={{ flex: 1, minWidth: '240px' }}
            />
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '8px 20px' }}>
              {loading ? (
                <><Loader2 size={16} className="spin-icon" /> Extracting AI Context...</>
              ) : (
                <><Upload size={16} /> Upload & Extract Context</>
              )}
            </button>
          </div>
        </form>

        {loading && (
          <div style={{ marginTop: '16px', padding: '12px 16px', background: 'var(--surface-container-low)', borderRadius: '8px', border: '1px solid rgba(37, 99, 235, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: 'var(--primary)', fontWeight: 600 }}>
              <Loader2 size={16} className="spin-icon" />
              <span>Analyzing document with LLM to auto-build experiences, projects, and metrics...</span>
            </div>
          </div>
        )}

        {resumes.length > 0 && (
          <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--outline)', letterSpacing: '0.5px', marginBottom: '10px', textTransform: 'uppercase' }}>Upload History</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {resumes.map((r) => (
                <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--surface-container-low)', borderRadius: '6px', fontSize: '13px' }}>
                  <span style={{ fontWeight: 500 }}>📄 {r.file_name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`chip chip-${r.parsed_status === 'done' ? 'personalized' : 'queued'}`} style={{ fontSize: '11px' }}>{r.parsed_status}</span>
                    <button className="btn btn-secondary btn-sm" style={{ padding: '3px 7px' }} title="Delete Resume" onClick={() => handleDeleteResume(r.id)}>
                      <Trash2 size={13} color="var(--error)" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {initialLoading ? (
        <>
          <SkeletonCard height="160px" />
          <SkeletonCard height="220px" />
          <SkeletonCard height="220px" />
        </>
      ) : (
        <>
          {/* Target Job Preferences Card */}
          <div className="card" style={{ borderLeft: '4px solid var(--primary)', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div className="card-header" style={{ marginBottom: '12px' }}>
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '17px', fontWeight: 600 }}>
                <Target size={18} color="var(--primary)" /> Target Job Preferences (Auto-Discover Keywords)
              </h3>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginBottom: '16px' }}>
              Configured target roles and salary filters utilized by the 1-Click Auto-Discover Search tool.
            </p>
            <form onSubmit={handleUpdateJobPref}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Role 1 (Primary)</label>
                  <input type="text" className="form-input" value={jobPref.role_1 || ''} onChange={(e) => setJobPref({ ...jobPref, role_1: e.target.value })} placeholder="e.g. Full Stack Developer" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Role 2</label>
                  <input type="text" className="form-input" value={jobPref.role_2 || ''} onChange={(e) => setJobPref({ ...jobPref, role_2: e.target.value })} placeholder="e.g. Backend Engineer" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Role 3</label>
                  <input type="text" className="form-input" value={jobPref.role_3 || ''} onChange={(e) => setJobPref({ ...jobPref, role_3: e.target.value })} placeholder="e.g. React Developer" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Min LPA</label>
                  <input type="number" step="0.5" className="form-input" value={jobPref.min_lpa || ''} onChange={(e) => setJobPref({ ...jobPref, min_lpa: e.target.value })} placeholder="e.g. 6" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Max LPA</label>
                  <input type="number" step="0.5" className="form-input" value={jobPref.max_lpa || ''} onChange={(e) => setJobPref({ ...jobPref, max_lpa: e.target.value })} placeholder="e.g. 18" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Locations</label>
                  <input type="text" className="form-input" value={jobPref.locations || ''} onChange={(e) => setJobPref({ ...jobPref, locations: e.target.value })} placeholder="e.g. Bangalore, Remote" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Experience Level</label>
                  <select className="form-select" value={jobPref.experience_level || 'fresher'} onChange={(e) => setJobPref({ ...jobPref, experience_level: e.target.value })}>
                    <option value="fresher">Fresher (0-1 yrs)</option>
                    <option value="junior">Junior (1-3 yrs)</option>
                    <option value="mid">Mid Level (3-5 yrs)</option>
                    <option value="senior">Senior (5+ yrs)</option>
                  </select>
                </div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm" style={{ marginTop: '14px', padding: '6px 14px' }} disabled={savingJobPref}>
                {savingJobPref ? (
                  <><Loader2 size={14} className="spin-icon" /> Saving...</>
                ) : (
                  <><Check size={14} /> Save Preferences</>
                )}
              </button>
            </form>
          </div>

          {/* Profile Card */}
          <div className="card" style={{ borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div className="card-header" style={{ marginBottom: '14px' }}>
              <h3 className="card-title" style={{ fontSize: '17px', fontWeight: 600 }}>Context Profile</h3>
            </div>
            <form onSubmit={handleUpdateProfile}>
              <div style={{ marginBottom: '16px' }}>
                <label className="form-label" style={{ fontSize: '12px', fontWeight: 600, marginBottom: '8px', display: 'block' }}>Employment Status</label>
                <div style={{ display: 'flex', gap: '20px', fontSize: '13px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="empStatus"
                      value="fresher"
                      checked={profile.is_fresher !== false && (!profile.role_title || profile.role_title.trim() === '')}
                      onChange={() => setProfile((prev: any) => ({ ...prev, role_title: '', is_fresher: true }))}
                    />
                    <span><strong>Fresher / Student / Seeking Opportunities</strong></span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="empStatus"
                      value="employed"
                      checked={profile.is_fresher === false || Boolean(profile.role_title && profile.role_title.trim() !== '')}
                      onChange={() => setProfile((prev: any) => ({ ...prev, is_fresher: false }))}
                    />
                    <span><strong>Currently Employed</strong></span>
                  </label>
                </div>
              </div>

              {/* Full Name — full-width, prominent, with warning if empty */}
              <div className="form-group" style={{ marginTop: '14px' }}>
                <label className="form-label" style={{ fontSize: '13px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  Full Name
                  {!profile.full_name && (
                    <span style={{ fontSize: '11px', fontWeight: 500, color: '#f97316', background: 'rgba(249,115,22,0.12)', border: '1px solid rgba(249,115,22,0.3)', borderRadius: '4px', padding: '1px 6px' }}>
                      ⚠ Required — used in all email sign-offs
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={profile.full_name || ''}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="e.g. Aditya Keerti"
                  style={!profile.full_name ? { borderColor: 'rgba(249,115,22,0.6)', boxShadow: '0 0 0 2px rgba(249,115,22,0.12)' } : {}}
                />
                {!profile.full_name && (
                  <p style={{ fontSize: '11px', color: '#f97316', marginTop: '4px', opacity: 0.9 }}>
                    Without a Full Name, emails will show your Gmail prefix instead of your real name.
                  </p>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginTop: '4px' }}>
                <div style={{ display: 'none' }}>{/* Full Name moved above */}</div>
                {profile.is_fresher === false || (profile.is_fresher === undefined && Boolean(profile.role_title && profile.role_title.trim() !== '')) ? (
                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Current Job Title</label>
                    <input type="text" className="form-input" value={profile.role_title || ''} onChange={(e) => setProfile({ ...profile, role_title: e.target.value })} placeholder="e.g. Full Stack Engineer" />
                  </div>
                ) : null}
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Graduation Year</label>
                  <input type="text" className="form-input" value={profile.grad_year || ''} onChange={(e) => setProfile({ ...profile, grad_year: e.target.value })} placeholder="e.g. 2027" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Portfolio URL</label>
                  <input type="text" className="form-input" value={profile.portfolio_url || ''} onChange={(e) => setProfile({ ...profile, portfolio_url: e.target.value })} placeholder="adityakeerti.vercel.app" />
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>GitHub URL</label>
                  <input type="text" className="form-input" value={profile.github_url || ''} onChange={(e) => setProfile({ ...profile, github_url: e.target.value })} placeholder="github.com/Adityakeerti" />
                </div>
              </div>
              <button type="submit" className="btn btn-secondary btn-sm" style={{ marginTop: '14px', padding: '6px 14px' }} disabled={savingProfile}>
                {savingProfile ? (
                  <><Loader2 size={14} className="spin-icon" /> Saving Profile...</>
                ) : (
                  <><Check size={14} /> Save Profile Changes</>
                )}
              </button>
            </form>
          </div>

          {/* Experience Section */}
          <div className="card" style={{ borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div className="card-header" style={{ marginBottom: '16px' }}>
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '17px', fontWeight: 600 }}>
                <Briefcase size={18} color="var(--primary)" /> Experience Entries ({experiences.length})
              </h3>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setShowAddExp(!showAddExp)}
                style={{ fontSize: '12px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                {showAddExp ? <><X size={14} /> Close</> : <><Plus size={14} /> Add Experience</>}
              </button>
            </div>

            {/* Form to Add New Experience */}
            {showAddExp && (
              <form onSubmit={handleAddExperience} style={{ background: 'var(--surface-container-low)', padding: '18px', borderRadius: '10px', marginBottom: '20px', border: '1px solid var(--primary-container)' }}>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '12px', color: 'var(--primary)' }}>Add New Experience</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <input type="text" className="form-input" placeholder="Title / Role (e.g. Senior Frontend Dev at Acme)" value={newExp.title} onChange={(e) => setNewExp({ ...newExp, title: e.target.value })} required />
                  <input type="text" className="form-input" placeholder="Dates (e.g. Jan 2022 - Present)" value={newExp.dates} onChange={(e) => setNewExp({ ...newExp, dates: e.target.value })} />
                  <textarea className="form-input" rows={2} style={{ gridColumn: '1 / -1' }} placeholder="Plain Summary / Highlights (e.g. Built micro-frontend infrastructure for 500k active users)" value={newExp.one_liner} onChange={(e) => setNewExp({ ...newExp, one_liner: e.target.value })} required />
                  <input type="text" className="form-input" placeholder="Tech Stack (comma separated: React, TS, Redux)" value={newExp.stack} onChange={(e) => setNewExp({ ...newExp, stack: e.target.value })} />
                  <input type="text" className="form-input" placeholder="Tags (comma separated: frontend, web)" value={newExp.tags} onChange={(e) => setNewExp({ ...newExp, tags: e.target.value })} />
                  <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' }}>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddExp(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary btn-sm" disabled={addingExp}>
                      {addingExp ? <><Loader2 size={14} className="spin-icon" /> Adding...</> : <><Plus size={14} /> Save New Experience</>}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* List of Experience Entries */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {experiences.map((exp) => (
                <div 
                  key={exp.id} 
                  style={{ 
                    padding: '16px', 
                    borderRadius: '10px', 
                    background: editingExpId === exp.id ? 'var(--surface-container-low)' : 'var(--surface-container-lowest)', 
                    border: editingExpId === exp.id ? '2px solid var(--primary)' : '1px solid var(--border)',
                    boxShadow: editingExpId === exp.id ? '0 4px 14px rgba(37, 99, 235, 0.12)' : '0 2px 4px rgba(0,0,0,0.01)',
                    transition: 'all 200ms ease'
                  }}
                >
                  {editingExpId === exp.id ? (
                    <form onSubmit={(e) => handleSaveExperience(e, exp.id)} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Edit2 size={15} /> Edit Experience Entry
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--outline)' }}>ID #{exp.id}</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Title / Role & Company</label>
                          <input type="text" className="form-input" value={editExpForm.title} onChange={(e) => setEditExpForm({ ...editExpForm, title: e.target.value })} required />
                        </div>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Duration / Dates</label>
                          <input type="text" className="form-input" value={editExpForm.dates} onChange={(e) => setEditExpForm({ ...editExpForm, dates: e.target.value })} />
                        </div>
                      </div>
                      <div>
                        <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Summary & Key Accomplishments</label>
                        <textarea className="form-input" rows={3} value={editExpForm.one_liner} onChange={(e) => setEditExpForm({ ...editExpForm, one_liner: e.target.value })} required style={{ lineHeight: '1.4' }} />
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Tech Stack (comma separated)</label>
                          <input type="text" className="form-input" value={editExpForm.stack} onChange={(e) => setEditExpForm({ ...editExpForm, stack: e.target.value })} />
                        </div>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Tags (comma separated)</label>
                          <input type="text" className="form-input" value={editExpForm.tags} onChange={(e) => setEditExpForm({ ...editExpForm, tags: e.target.value })} />
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '6px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditingExpId(null)}>
                          <X size={14} /> Cancel
                        </button>
                        <button type="submit" className="btn btn-primary btn-sm" style={{ padding: '6px 16px' }} disabled={savingExpId === exp.id}>
                          {savingExpId === exp.id ? <><Loader2 size={14} className="spin-icon" /> Saving...</> : <><Save size={14} /> Save Experience</>}
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--on-surface)' }}>{exp.title}</div>
                          {exp.dates && <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)', marginTop: '2px' }}>🗓️ {exp.dates}</div>}
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button className="btn btn-secondary btn-sm" style={{ padding: '4px 8px' }} title="Edit Entry" onClick={() => startEditExperience(exp)}>
                            <Edit2 size={14} color="var(--primary)" /> <span style={{ fontSize: '12px' }}>Edit</span>
                          </button>
                          <button className="btn btn-secondary btn-sm" style={{ padding: '4px 8px' }} title="Delete Entry" onClick={async () => { if (window.confirm("Are you sure you want to delete this experience entry?")) { await api.deleteExperience(exp.id); loadData(); } }}>
                            <Trash2 size={14} color="var(--error)" />
                          </button>
                        </div>
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginTop: '8px', lineHeight: '1.5' }}>{exp.one_liner}</p>
                      {exp.stack && exp.stack.length > 0 && (
                        <div style={{ display: 'flex', gap: '6px', marginTop: '10px', flexWrap: 'wrap' }}>
                          {exp.stack.map((s: string, idx: number) => (
                            <span key={idx} className="chip chip-new" style={{ fontSize: '11px', padding: '2px 8px' }}>{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {experiences.length === 0 && !showAddExp && (
                <div style={{ textAlign: 'center', padding: '24px', color: 'var(--outline)', fontSize: '14px' }}>
                  No experience entries added yet. Upload a resume or click "+ Add Experience" above.
                </div>
              )}
            </div>
          </div>

          {/* Projects Section */}
          <div className="card" style={{ borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div className="card-header" style={{ marginBottom: '16px' }}>
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '17px', fontWeight: 600 }}>
                <FolderGit2 size={18} color="var(--primary)" /> Portfolio Projects ({projects.length})
              </h3>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setShowAddProj(!showAddProj)}
                style={{ fontSize: '12px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                {showAddProj ? <><X size={14} /> Close</> : <><Plus size={14} /> Add Project</>}
              </button>
            </div>

            {/* Form to Add New Project */}
            {showAddProj && (
              <form onSubmit={handleAddProject} style={{ background: 'var(--surface-container-low)', padding: '18px', borderRadius: '10px', marginBottom: '20px', border: '1px solid var(--primary-container)' }}>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '12px', color: 'var(--primary)' }}>Add Portfolio Project</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <input type="text" className="form-input" placeholder="Project Title (e.g. Distributed Task Queue)" value={newProj.title} onChange={(e) => setNewProj({ ...newProj, title: e.target.value })} required />
                  <input type="text" className="form-input" placeholder="Project Link (e.g. https://github.com/user/repo)" value={newProj.link} onChange={(e) => setNewProj({ ...newProj, link: e.target.value })} />
                  <textarea className="form-input" rows={2} style={{ gridColumn: '1 / -1' }} placeholder="Summary & Key Technical Highlights" value={newProj.one_liner} onChange={(e) => setNewProj({ ...newProj, one_liner: e.target.value })} required />
                  <input type="text" className="form-input" placeholder="Tech Stack (comma separated: Go, Redis, Docker)" value={newProj.stack} onChange={(e) => setNewProj({ ...newProj, stack: e.target.value })} />
                  <input type="text" className="form-input" placeholder="Tags (comma separated: backend, distributed)" value={newProj.tags} onChange={(e) => setNewProj({ ...newProj, tags: e.target.value })} />
                  <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' }}>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddProj(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary btn-sm" disabled={addingProj}>
                      {addingProj ? <><Loader2 size={14} className="spin-icon" /> Adding...</> : <><Plus size={14} /> Save New Project</>}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* List of Project Entries */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {projects.map((proj) => (
                <div 
                  key={proj.id} 
                  style={{ 
                    padding: '16px', 
                    borderRadius: '10px', 
                    background: editingProjId === proj.id ? 'var(--surface-container-low)' : 'var(--surface-container-lowest)', 
                    border: editingProjId === proj.id ? '2px solid var(--primary)' : '1px solid var(--border)',
                    boxShadow: editingProjId === proj.id ? '0 4px 14px rgba(37, 99, 235, 0.12)' : '0 2px 4px rgba(0,0,0,0.01)',
                    transition: 'all 200ms ease'
                  }}
                >
                  {editingProjId === proj.id ? (
                    <form onSubmit={(e) => handleSaveProject(e, proj.id)} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Edit2 size={15} /> Edit Project Entry
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--outline)' }}>ID #{proj.id}</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Project Title</label>
                          <input type="text" className="form-input" value={editProjForm.title} onChange={(e) => setEditProjForm({ ...editProjForm, title: e.target.value })} required />
                        </div>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Project Link / GitHub</label>
                          <input type="text" className="form-input" value={editProjForm.link} onChange={(e) => setEditProjForm({ ...editProjForm, link: e.target.value })} />
                        </div>
                      </div>
                      <div>
                        <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Summary & Problem Solved</label>
                        <textarea className="form-input" rows={3} value={editProjForm.one_liner} onChange={(e) => setEditProjForm({ ...editProjForm, one_liner: e.target.value })} required style={{ lineHeight: '1.4' }} />
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Tech Stack (comma separated)</label>
                          <input type="text" className="form-input" value={editProjForm.stack} onChange={(e) => setEditProjForm({ ...editProjForm, stack: e.target.value })} />
                        </div>
                        <div>
                          <label className="form-label" style={{ fontSize: '12px', fontWeight: 600 }}>Tags (comma separated)</label>
                          <input type="text" className="form-input" value={editProjForm.tags} onChange={(e) => setEditProjForm({ ...editProjForm, tags: e.target.value })} />
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '6px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditingProjId(null)}>
                          <X size={14} /> Cancel
                        </button>
                        <button type="submit" className="btn btn-primary btn-sm" style={{ padding: '6px 16px' }} disabled={savingProjId === proj.id}>
                          {savingProjId === proj.id ? <><Loader2 size={14} className="spin-icon" /> Saving...</> : <><Save size={14} /> Save Project</>}
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--on-surface)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {proj.title}
                            {proj.link && (
                              <a href={proj.link} target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: 'var(--primary)', display: 'inline-flex', alignItems: 'center', gap: '3px', textDecoration: 'none' }}>
                                <ExternalLink size={12} /> Link
                              </a>
                            )}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button className="btn btn-secondary btn-sm" style={{ padding: '4px 8px' }} title="Edit Entry" onClick={() => startEditProject(proj)}>
                            <Edit2 size={14} color="var(--primary)" /> <span style={{ fontSize: '12px' }}>Edit</span>
                          </button>
                          <button className="btn btn-secondary btn-sm" style={{ padding: '4px 8px' }} title="Delete Entry" onClick={async () => { if (window.confirm("Are you sure you want to delete this project entry?")) { await api.deleteProject(proj.id); loadData(); } }}>
                            <Trash2 size={14} color="var(--error)" />
                          </button>
                        </div>
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginTop: '8px', lineHeight: '1.5' }}>{proj.one_liner}</p>
                      {proj.stack && proj.stack.length > 0 && (
                        <div style={{ display: 'flex', gap: '6px', marginTop: '10px', flexWrap: 'wrap' }}>
                          {proj.stack.map((s: string, idx: number) => (
                            <span key={idx} className="chip chip-personalized" style={{ fontSize: '11px', padding: '2px 8px' }}>{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {projects.length === 0 && !showAddProj && (
                <div style={{ textAlign: 'center', padding: '24px', color: 'var(--outline)', fontSize: '14px' }}>
                  No portfolio projects added yet. Upload a resume or click "+ Add Project" above.
                </div>
              )}
            </div>
          </div>

          {/* Key Achievements & Metrics Section */}
          <div className="card" style={{ borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.03)' }}>
            <div className="card-header" style={{ marginBottom: '16px' }}>
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '17px', fontWeight: 600 }}>
                <Award size={18} color="var(--primary)" /> Key Achievements & Quantifiable Metrics ({achievements.length})
              </h3>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setShowAddAch(!showAddAch)}
                style={{ fontSize: '12px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                {showAddAch ? <><X size={14} /> Close</> : <><Plus size={14} /> Add Achievement</>}
              </button>
            </div>

            {/* Form to Add New Achievement */}
            {showAddAch && (
              <form onSubmit={handleAddAchievement} style={{ background: 'var(--surface-container-low)', padding: '16px', borderRadius: '10px', marginBottom: '20px', border: '1px solid var(--primary-container)', display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ flex: 1 }}
                  placeholder="Enter key metric (e.g. Scaled database throughput by 40% using Redis caching)"
                  value={newAchText}
                  onChange={(e) => setNewAchText(e.target.value)}
                  required
                />
                <button type="submit" className="btn btn-primary btn-sm" disabled={addingAch}>
                  {addingAch ? <><Loader2 size={14} className="spin-icon" /> Adding...</> : <><Plus size={14} /> Save</>}
                </button>
              </form>
            )}

            {/* List of Achievement Entries */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {achievements.map((ach) => (
                <div 
                  key={ach.id} 
                  style={{ 
                    padding: '12px 16px', 
                    borderRadius: '8px', 
                    background: editingAchId === ach.id ? 'var(--surface-container-low)' : 'var(--surface-container-lowest)', 
                    border: editingAchId === ach.id ? '2px solid var(--primary)' : '1px solid var(--border)',
                    transition: 'all 200ms ease'
                  }}
                >
                  {editingAchId === ach.id ? (
                    <form onSubmit={(e) => handleSaveAchievement(e, ach.id)} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <input type="text" className="form-input" style={{ flex: 1 }} value={editAchText} onChange={(e) => setEditAchText(e.target.value)} required />
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditingAchId(null)}>
                        <X size={14} /> Cancel
                      </button>
                      <button type="submit" className="btn btn-primary btn-sm" disabled={savingAchId === ach.id}>
                        {savingAchId === ach.id ? <><Loader2 size={14} className="spin-icon" /> Saving...</> : <><Save size={14} /> Save</>}
                      </button>
                    </form>
                  ) : (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '13px', color: 'var(--on-surface)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: '#eab308' }}>🏆</span> {ach.text}
                      </span>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button className="btn btn-secondary btn-sm" style={{ padding: '3px 7px' }} title="Edit Achievement" onClick={() => startEditAchievement(ach)}>
                          <Edit2 size={13} color="var(--primary)" />
                        </button>
                        <button className="btn btn-secondary btn-sm" style={{ padding: '3px 7px' }} title="Delete Achievement" onClick={async () => { if (window.confirm("Are you sure you want to delete this achievement entry?")) { await api.deleteAchievement(ach.id); loadData(); } }}>
                          <Trash2 size={13} color="var(--error)" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {achievements.length === 0 && !showAddAch && (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--outline)', fontSize: '13px' }}>
                  No achievements recorded. Upload a resume or click "+ Add Achievement" above.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
