import React, { useState, useEffect } from 'react';
import { Upload, Plus, Trash2, Check, FileText, Briefcase, FolderGit2 } from 'lucide-react';
import { api } from '../api';

export const ResumeContextView: React.FC = () => {
  const [resumes, setResumes] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>({});
  const [experiences, setExperiences] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [file, setFile] = useState<File | null>(null);

  // New Item States
  const [newExp, setNewExp] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '' });
  const [newProj, setNewProj] = useState({ title: '', dates: '', one_liner: '', stack: '', tags: '', link: '' });

  const loadData = async () => {
    try {
      const [resList, profData, expList, projList] = await Promise.all([
        api.listResumes(),
        api.getProfile(),
        api.listExperiences(),
        api.listProjects(),
      ]);
      setResumes(resList);
      setProfile(profData);
      setExperiences(expList);
      setProjects(projList);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.uploadResume(formData);
      setMsg('Resume uploaded! Background parser triggered using High-Tier LLM.');
      setFile(null);
      await loadData();
    } catch (err: any) {
      setMsg('Upload error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updateProfile(profile);
      setMsg('Profile updated successfully!');
    } catch (err: any) {
      setMsg('Error updating profile: ' + err.message);
    }
  };

  const handleAddExperience = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createExperience({
        ...newExp,
        stack: newExp.stack ? newExp.stack.split(',').map((s) => s.trim()) : [],
        tags: newExp.tags ? newExp.tags.split(',').map((t) => t.trim()) : [],
      });
      setNewExp({ title: '', dates: '', one_liner: '', stack: '', tags: '' });
      await loadData();
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createProject({
        ...newProj,
        stack: newProj.stack ? newProj.stack.split(',').map((s) => s.trim()) : [],
        tags: newProj.tags ? newProj.tags.split(',').map((t) => t.trim()) : [],
      });
      setNewProj({ title: '', dates: '', one_liner: '', stack: '', tags: '', link: '' });
      await loadData();
    } catch (err: any) {
      console.error(err);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Resume & Dynamic Context Engine</h1>
          <p className="page-subtitle">Upload your resume to seed your context layer or edit your profile & portfolio</p>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}

      {/* Resume Upload Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={18} color="var(--primary)" /> Resume Parser (LLM Auto-Extraction)
          </h3>
        </div>
        <form onSubmit={handleUploadResume} style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <input
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            className="form-input"
            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            required
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            <Upload size={16} /> {loading ? 'Uploading...' : 'Upload & Parse'}
          </button>
        </form>

        {resumes.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--outline)', marginBottom: '8px' }}>UPLOAD HISTORY</div>
            {resumes.map((r) => (
              <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-container-low)', borderRadius: '4px', marginBottom: '6px', fontSize: '13px' }}>
                <span>📄 {r.file_name}</span>
                <span className={`chip chip-${r.parsed_status === 'done' ? 'personalized' : 'queued'}`}>{r.parsed_status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Profile Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Context Profile</h3>
        </div>
        <form onSubmit={handleUpdateProfile}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Role Title</label>
              <input type="text" className="form-input" value={profile.role_title || ''} onChange={(e) => setProfile({ ...profile, role_title: e.target.value })} placeholder="e.g. Full Stack Software Engineer" />
            </div>
            <div className="form-group">
              <label className="form-label">Graduation Year</label>
              <input type="text" className="form-input" value={profile.grad_year || ''} onChange={(e) => setProfile({ ...profile, grad_year: e.target.value })} placeholder="e.g. 2024" />
            </div>
            <div className="form-group">
              <label className="form-label">Portfolio URL</label>
              <input type="text" className="form-input" value={profile.portfolio_url || ''} onChange={(e) => setProfile({ ...profile, portfolio_url: e.target.value })} placeholder="https://yourportfolio.dev" />
            </div>
            <div className="form-group">
              <label className="form-label">GitHub URL</label>
              <input type="text" className="form-input" value={profile.github_url || ''} onChange={(e) => setProfile({ ...profile, github_url: e.target.value })} placeholder="https://github.com/username" />
            </div>
          </div>
          <button type="submit" className="btn btn-secondary btn-sm" style={{ marginTop: '12px' }}>
            <Check size={14} /> Save Profile Changes
          </button>
        </form>
      </div>

      {/* Experience Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Briefcase size={18} /> Experience Entries ({experiences.length})
          </h3>
        </div>
        {experiences.map((exp) => (
          <div key={exp.id} style={{ borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '15px' }}>{exp.title}</strong>
              <button className="btn btn-secondary btn-sm" onClick={async () => { await api.deleteExperience(exp.id); loadData(); }}>
                <Trash2 size={14} color="var(--error)" />
              </button>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginTop: '4px' }}>{exp.one_liner}</p>
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
              {exp.stack?.map((s: string, idx: number) => <span key={idx} className="chip chip-new">{s}</span>)}
            </div>
          </div>
        ))}

        <form onSubmit={handleAddExperience} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'var(--surface-container-low)', padding: '16px', borderRadius: '6px', marginTop: '16px' }}>
          <input type="text" className="form-input" placeholder="Title / Role" value={newExp.title} onChange={(e) => setNewExp({ ...newExp, title: e.target.value })} required />
          <input type="text" className="form-input" placeholder="Dates (e.g. 2022-2024)" value={newExp.dates} onChange={(e) => setNewExp({ ...newExp, dates: e.target.value })} />
          <input type="text" className="form-input" style={{ gridColumn: '1 / -1' }} placeholder="Plain One Liner Summary (No superlatives)" value={newExp.one_liner} onChange={(e) => setNewExp({ ...newExp, one_liner: e.target.value })} required />
          <input type="text" className="form-input" placeholder="Stack (comma separated)" value={newExp.stack} onChange={(e) => setNewExp({ ...newExp, stack: e.target.value })} />
          <input type="text" className="form-input" placeholder="Tags (comma separated)" value={newExp.tags} onChange={(e) => setNewExp({ ...newExp, tags: e.target.value })} />
          <button type="submit" className="btn btn-primary btn-sm" style={{ gridColumn: '1 / -1' }}><Plus size={14} /> Add Experience</button>
        </form>
      </div>

      {/* Projects Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderGit2 size={18} /> Portfolio Projects ({projects.length})
          </h3>
        </div>
        {projects.map((proj) => (
          <div key={proj.id} style={{ borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '15px' }}>{proj.title}</strong>
              <button className="btn btn-secondary btn-sm" onClick={async () => { await api.deleteProject(proj.id); loadData(); }}>
                <Trash2 size={14} color="var(--error)" />
              </button>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginTop: '4px' }}>{proj.one_liner}</p>
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
              {proj.stack?.map((s: string, idx: number) => <span key={idx} className="chip chip-personalized">{s}</span>)}
            </div>
          </div>
        ))}

        <form onSubmit={handleAddProject} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'var(--surface-container-low)', padding: '16px', borderRadius: '6px', marginTop: '16px' }}>
          <input type="text" className="form-input" placeholder="Project Title" value={newProj.title} onChange={(e) => setNewProj({ ...newProj, title: e.target.value })} required />
          <input type="text" className="form-input" placeholder="Project Link" value={newProj.link} onChange={(e) => setNewProj({ ...newProj, link: e.target.value })} />
          <input type="text" className="form-input" style={{ gridColumn: '1 / -1' }} placeholder="Plain Summary & Problem Solved" value={newProj.one_liner} onChange={(e) => setNewProj({ ...newProj, one_liner: e.target.value })} required />
          <input type="text" className="form-input" placeholder="Stack (comma separated)" value={newProj.stack} onChange={(e) => setNewProj({ ...newProj, stack: e.target.value })} />
          <input type="text" className="form-input" placeholder="Tags (comma separated)" value={newProj.tags} onChange={(e) => setNewProj({ ...newProj, tags: e.target.value })} />
          <button type="submit" className="btn btn-primary btn-sm" style={{ gridColumn: '1 / -1' }}><Plus size={14} /> Add Project</button>
        </form>
      </div>
    </div>
  );
};
