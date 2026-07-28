import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Check, HelpCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import { SkeletonCard } from './Skeleton';

interface TemplatesViewProps {
  onLoadingChange?: (loading: boolean) => void;
}

export const TemplatesView: React.FC<TemplatesViewProps> = ({ onLoadingChange }) => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<any | null>(null);
  const [newCategory, setNewCategory] = useState('');
  const [newSubject, setNewSubject] = useState('');
  const [newBody, setNewBody] = useState('');

  const loadTemplates = async () => {
    onLoadingChange?.(true);
    try {
      const items = await api.listTemplates();
      setTemplates(items);
    } catch (e: any) {
      console.error(e);
    } finally {
      setInitialLoading(false);
      onLoadingChange?.(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingTemplate(true);
    try {
      if (editingTemplate?.id) {
        await api.updateTemplate(editingTemplate.id, {
          category: newCategory,
          subject_template: newSubject,
          body_template: newBody,
        });
      } else {
        await api.createTemplate({
          category: newCategory,
          subject_template: newSubject,
          body_template: newBody,
        });
      }
      setEditingTemplate(null);
      setNewCategory('');
      setNewSubject('');
      setNewBody('');
      await loadTemplates();
    } catch (err: any) {
      console.error(err);
    } finally {
      setSavingTemplate(false);
    }
  };

  const startEdit = (tmpl: any) => {
    setEditingTemplate(tmpl);
    setNewCategory(tmpl.category);
    setNewSubject(tmpl.subject_template);
    setNewBody(tmpl.body_template);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Outreach Email Templates</h1>
          <p className="page-subtitle">Manage dynamic templates seeded per user account with placeholder tags</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingTemplate({ id: null });
            setNewCategory('');
            setNewSubject('');
            setNewBody('');
          }}
        >
          <Plus size={16} /> Create Template
        </button>
      </div>

      <div className="card" style={{ background: '#eff6ff', borderColor: '#bfdbfe' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px', color: 'var(--primary)', fontWeight: 600, fontSize: '14px' }}>
          <HelpCircle size={16} /> Available Dynamic Placeholder Tags:
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {['RECIPIENT_NAME', 'COMPANY', 'ROLE_TITLE', 'USER_NAME', 'PORTFOLIO_URL', 'GITHUB_URL', 'PERSONAL_HOOK', 'RELEVANT_PROJECT_LINE', 'WHY_THIS_COMPANY'].map((tag) => (
            <span key={tag} className="chip chip-new" style={{ textTransform: 'none' }}>
              {`{{${tag}}}`}
            </span>
          ))}
        </div>
      </div>

      {editingTemplate && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">{editingTemplate.id ? 'Edit Template' : 'New Template'}</h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setEditingTemplate(null)}>Cancel</button>
          </div>
          <form onSubmit={handleSaveTemplate}>
            <div className="form-group">
              <label className="form-label">Category Name</label>
              <input type="text" className="form-input" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Subject Template</label>
              <input type="text" className="form-input" value={newSubject} onChange={(e) => setNewSubject(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Body Template</label>
              <textarea className="form-textarea" style={{ minHeight: '140px' }} value={newBody} onChange={(e) => setNewBody(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary" disabled={savingTemplate}>
              {savingTemplate ? (
                <><Loader2 size={16} className="spin-icon" /> Saving...</>
              ) : (
                <><Check size={16} /> Save Template</>
              )}
            </button>
          </form>
        </div>
      )}

      {initialLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
          <SkeletonCard height="180px" />
          <SkeletonCard height="180px" />
          <SkeletonCard height="180px" />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
          {templates.map((tmpl) => (
            <div key={tmpl.id} className="card" style={{ marginBottom: 0 }}>
              <div className="card-header">
                <span className="chip chip-personalized">{tmpl.category}</span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => startEdit(tmpl)}><Edit2 size={14} /></button>
                  <button className="btn btn-secondary btn-sm" onClick={async () => { if (window.confirm("Are you sure you want to delete this template?")) { await api.deleteTemplate(tmpl.id); loadTemplates(); } }}><Trash2 size={14} color="var(--error)" /></button>
                </div>
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>{tmpl.subject_template}</div>
              <div style={{ fontSize: '13px', color: 'var(--on-surface-variant)', background: 'var(--surface-container-low)', padding: '10px', borderRadius: '4px', whiteSpace: 'pre-wrap', maxHeight: '140px', overflowY: 'auto' }}>
                {tmpl.body_template}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
