import React, { useState, useEffect } from 'react';
import { Plus, Check, X, Sparkles, Eye, Trash2 } from 'lucide-react';
import { api } from '../api';

export const ContactsQueueView: React.FC = () => {
  const [contacts, setContacts] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);

  // Preview Modal
  const [selectedContact, setSelectedContact] = useState<any | null>(null);

  // New Contact Form Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newContact, setNewContact] = useState({
    name: '', company: '', role: '', email: '', source: 'manual', job_posting_url: ''
  });

  const loadData = async () => {
    try {
      const [cList, qList] = await Promise.all([
        api.listContacts(),
        api.listQueue(),
      ]);
      setContacts(cList);
      setQueue(qList);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createContact(newContact);
      setNewContact({ name: '', company: '', role: '', email: '', source: 'manual', job_posting_url: '' });
      setShowAddModal(false);
      await loadData();
    } catch (err: any) {
      setMsg('Error adding contact: ' + err.message);
    }
  };

  const handlePersonalize = async (id: number) => {
    setLoading(true);
    try {
      await api.personalizeContact(id);
      setMsg('LLM generated personalized email placeholders for contact!');
      await loadData();
    } catch (err: any) {
      setMsg('Personalize error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.approveQueueItem(id);
      setMsg('Contact approved and queued for send!');
      await loadData();
    } catch (err: any) {
      setMsg('Approval error: ' + err.message);
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.rejectQueueItem(id);
      setMsg('Contact rejected.');
      await loadData();
    } catch (err: any) {
      setMsg('Reject error: ' + err.message);
    }
  };

  const filteredContacts = statusFilter === 'all'
    ? contacts
    : contacts.filter((c) => c.status === statusFilter);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Contacts & Approval Queue</h1>
          <p className="page-subtitle">Manage discovered contacts, review LLM-personalized emails, and approve send queue</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> Add Contact
        </button>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}

      {/* Approval Queue Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="var(--primary)" /> Send Queue Approval ({queue.length})
          </h3>
        </div>
        {queue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '20px 0' }}>
            No contacts currently awaiting review or queue approval.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Contact</th>
                  <th>Company & Role</th>
                  <th>Status</th>
                  <th>Subject / Preview</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.name || 'Hiring Manager'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--outline)' }}>{item.email}</div>
                    </td>
                    <td>
                      <div>{item.company || 'N/A'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>{item.role || 'N/A'}</div>
                    </td>
                    <td><span className={`chip chip-${item.status}`}>{item.status}</span></td>
                    <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.subject ? item.subject : <span style={{ color: 'var(--outline)', fontStyle: 'italic' }}>Not personalized yet</span>}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {item.subject && (
                          <button className="btn btn-secondary btn-sm" onClick={() => setSelectedContact(item)}>
                            <Eye size={14} /> Preview
                          </button>
                        )}
                        {item.status === 'new' && (
                          <button className="btn btn-primary btn-sm" onClick={() => handlePersonalize(item.id)} disabled={loading}>
                            <Sparkles size={14} /> Personalize
                          </button>
                        )}
                        {item.status === 'personalized' && (
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(item.id)}>
                            <Check size={14} /> Approve
                          </button>
                        )}
                        <button className="btn btn-secondary btn-sm" onClick={() => handleReject(item.id)}>
                          <X size={14} color="var(--error)" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Contacts Store Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Contacts Directory ({contacts.length})</h3>
          <div style={{ display: 'flex', gap: '6px' }}>
            {['all', 'new', 'personalized', 'queued', 'sent', 'replied', 'bounced'].map((st) => (
              <button
                key={st}
                className={`btn btn-sm ${statusFilter === st ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter(st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Company</th>
                <th>Role</th>
                <th>Source</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredContacts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{c.name || 'Hiring Manager'}</div>
                    <div style={{ fontSize: '12px', color: 'var(--outline)' }}>{c.email}</div>
                  </td>
                  <td>{c.company || 'N/A'}</td>
                  <td>{c.role || 'N/A'}</td>
                  <td style={{ fontSize: '12px' }}>{c.source || 'manual'}</td>
                  <td><span className={`chip chip-${c.status}`}>{c.status}</span></td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {c.body && (
                        <button className="btn btn-secondary btn-sm" onClick={() => setSelectedContact(c)}>
                          <Eye size={14} />
                        </button>
                      )}
                      <button className="btn btn-secondary btn-sm" onClick={async () => { await api.deleteContact(c.id); loadData(); }}>
                        <Trash2 size={14} color="var(--error)" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Email Preview Modal */}
      {selectedContact && (
        <div className="modal-overlay" onClick={() => setSelectedContact(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="card-header">
              <h3 className="card-title">Email Preview</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedContact(null)}>
                <X size={14} />
              </button>
            </div>
            <div style={{ marginBottom: '16px', fontSize: '13px' }}>
              <div><strong>To:</strong> {selectedContact.name} &lt;{selectedContact.email}&gt;</div>
              <div><strong>Company:</strong> {selectedContact.company}</div>
              <div><strong>Subject:</strong> {selectedContact.subject}</div>
            </div>
            <div style={{ padding: '16px', background: 'var(--surface-container-low)', borderRadius: '6px', fontSize: '14px', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-geist)' }}>
              {selectedContact.body}
            </div>

            {selectedContact.personalized_data && (
              <div style={{ marginTop: '16px', padding: '12px', background: '#eff6ff', borderRadius: '6px', fontSize: '12px' }}>
                <strong style={{ color: 'var(--primary)' }}>LLM Dynamic Placeholders:</strong>
                <pre style={{ marginTop: '4px', whiteSpace: 'pre-wrap' }}>{JSON.stringify(selectedContact.personalized_data, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Contact Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="card-header">
              <h3 className="card-title">Add Contact</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAddModal(false)}>
                <X size={14} />
              </button>
            </div>
            <form onSubmit={handleAddContact}>
              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input type="email" className="form-input" value={newContact.email} onChange={(e) => setNewContact({ ...newContact, email: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Name</label>
                <input type="text" className="form-input" value={newContact.name} onChange={(e) => setNewContact({ ...newContact, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Company</label>
                <input type="text" className="form-input" value={newContact.company} onChange={(e) => setNewContact({ ...newContact, company: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Role Title</label>
                <input type="text" className="form-input" value={newContact.role} onChange={(e) => setNewContact({ ...newContact, role: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }}>
                Save Contact
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
