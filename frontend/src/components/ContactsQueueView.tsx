import React, { useState, useEffect } from 'react';
import { Plus, Check, X, Sparkles, Eye, Trash2, Loader2, ExternalLink, Send } from 'lucide-react';
import { api } from '../api';
import { SkeletonTable } from './Skeleton';

interface ContactsQueueViewProps {
  onLoadingChange?: (loading: boolean) => void;
}

export const ContactsQueueView: React.FC<ContactsQueueViewProps> = ({ onLoadingChange }) => {
  const [contacts, setContacts] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [genericQueue, setGenericQueue] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [msg, setMsg] = useState('');
  const [initialLoading, setInitialLoading] = useState(true);
  const [personalizingId, setPersonalizingId] = useState<number | null>(null);
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [sendingId, setSendingId] = useState<number | null>(null);

  // Row selection states
  const [selectedQueueIds, setSelectedQueueIds] = useState<number[]>([]);
  const [selectedGenericQueueIds, setSelectedGenericQueueIds] = useState<number[]>([]);
  const [selectedContactIds, setSelectedContactIds] = useState<number[]>([]);

  // Preview Modal
  const [selectedContact, setSelectedContact] = useState<any | null>(null);

  // New Contact Form Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [addingContact, setAddingContact] = useState(false);
  const [newContact, setNewContact] = useState({
    name: '', company: '', role: '', email: '', source: 'manual', job_posting_url: ''
  });

  const loadData = async () => {
    onLoadingChange?.(true);
    try {
      const [cList, qList, gList] = await Promise.all([
        api.listContacts(),
        api.listQueue(),
        api.listGenericQueue().catch(() => []),
      ]);
      setContacts(cList);
      setQueue(qList);
      setGenericQueue(gList);
      setSelectedQueueIds([]);
      setSelectedGenericQueueIds([]);
      setSelectedContactIds([]);
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

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingContact(true);
    try {
      await api.createContact(newContact);
      setNewContact({ name: '', company: '', role: '', email: '', source: 'manual', job_posting_url: '' });
      setShowAddModal(false);
      await loadData();
    } catch (err: any) {
      setMsg('Error adding contact: ' + err.message);
    } finally {
      setAddingContact(false);
    }
  };

  const handlePersonalize = async (id: number) => {
    setPersonalizingId(id);
    onLoadingChange?.(true);
    try {
      await api.personalizeContact(id);
      setMsg('LLM generated personalized email placeholders for contact!');
      await loadData();
    } catch (err: any) {
      setMsg('Personalize error: ' + err.message);
    } finally {
      setPersonalizingId(null);
      onLoadingChange?.(false);
    }
  };

  const handleApprove = async (id: number) => {
    setApprovingId(id);
    try {
      await api.approveQueueItem(id);
      setMsg('Contact approved and queued for send!');
      await loadData();
    } catch (err: any) {
      setMsg('Approval error: ' + err.message);
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (id: number) => {
    setRejectingId(id);
    try {
      await api.rejectQueueItem(id);
      setMsg('Contact rejected.');
      await loadData();
    } catch (err: any) {
      setMsg('Reject error: ' + err.message);
    } finally {
      setRejectingId(null);
    }
  };

  const handleSendNow = async (id: number) => {
    setSendingId(id);
    onLoadingChange?.(true);
    try {
      await api.sendMailNow(id);
      setMsg('✅ Email sent successfully!');
      await loadData();
    } catch (err: any) {
      setMsg('Send error: ' + err.message);
    } finally {
      setSendingId(null);
      onLoadingChange?.(false);
    }
  };

  // Bulk Handlers
  const handleBulkApproveQueue = async () => {
    if (selectedQueueIds.length === 0) return;
    onLoadingChange?.(true);
    try {
      await api.bulkApproveQueueItems(selectedQueueIds);
      setMsg(`✅ Bulk approved ${selectedQueueIds.length} contacts!`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk approval error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkRejectQueue = async () => {
    if (selectedQueueIds.length === 0) return;
    onLoadingChange?.(true);
    try {
      await api.bulkRejectQueueItems(selectedQueueIds);
      setMsg(`Bulk rejected ${selectedQueueIds.length} contacts.`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk reject error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkDeleteQueue = async () => {
    if (selectedQueueIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedQueueIds.length} selected contacts entirely from the database?`)) return;
    onLoadingChange?.(true);
    try {
      await api.bulkDeleteContacts(selectedQueueIds);
      setMsg(`Bulk deleted ${selectedQueueIds.length} contacts.`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk delete error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkApproveGenericQueue = async () => {
    if (selectedGenericQueueIds.length === 0) return;
    onLoadingChange?.(true);
    try {
      await api.bulkApproveQueueItems(selectedGenericQueueIds);
      setMsg(`✅ Bulk approved ${selectedGenericQueueIds.length} generic contacts!`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk approval error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkRejectGenericQueue = async () => {
    if (selectedGenericQueueIds.length === 0) return;
    onLoadingChange?.(true);
    try {
      await api.bulkRejectQueueItems(selectedGenericQueueIds);
      setMsg(`Bulk rejected ${selectedGenericQueueIds.length} generic contacts.`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk reject error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkDeleteGenericQueue = async () => {
    if (selectedGenericQueueIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedGenericQueueIds.length} selected generic contacts entirely from the database?`)) return;
    onLoadingChange?.(true);
    try {
      await api.bulkDeleteContacts(selectedGenericQueueIds);
      setMsg(`Bulk deleted ${selectedGenericQueueIds.length} generic contacts.`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk delete error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
    }
  };

  const handleBulkDeleteContacts = async () => {
    if (selectedContactIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedContactIds.length} selected contacts entirely from the database?`)) return;
    onLoadingChange?.(true);
    try {
      await api.bulkDeleteContacts(selectedContactIds);
      setMsg(`Bulk deleted ${selectedContactIds.length} contacts.`);
      await loadData();
    } catch (err: any) {
      setMsg('Bulk delete error: ' + err.message);
    } finally {
      onLoadingChange?.(false);
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
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="var(--primary)" /> Send Queue Approval ({queue.length})
          </h3>
        </div>

        <div style={{ padding: '0 16px' }}>
          {selectedQueueIds.length > 0 && (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '12px 16px', background: 'var(--surface-container-high)', borderRadius: '6px', marginBottom: '12px', marginTop: '12px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>{selectedQueueIds.length} items selected:</span>
              <button className="btn btn-primary btn-sm" onClick={handleBulkApproveQueue}>Approve Selected</button>
              <button className="btn btn-secondary btn-sm" onClick={handleBulkRejectQueue}>Reject Selected</button>
              <button className="btn btn-danger btn-sm" style={{ backgroundColor: 'var(--error)', color: 'white', borderColor: 'var(--error)' }} onClick={handleBulkDeleteQueue}>Delete Selected</button>
            </div>
          )}
        </div>

        {initialLoading ? (
          <SkeletonTable rows={3} columns={5} />
        ) : queue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '20px 0' }}>
            No contacts currently awaiting review or queue approval.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={queue.length > 0 && selectedQueueIds.length === queue.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedQueueIds(queue.map(q => q.id));
                        } else {
                          setSelectedQueueIds([]);
                        }
                      }}
                    />
                  </th>
                  <th>Contact</th>
                  <th>Company & Role</th>
                  <th>JD</th>
                  <th>Status</th>
                  <th>Subject / Preview</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedQueueIds.includes(item.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedQueueIds([...selectedQueueIds, item.id]);
                          } else {
                            setSelectedQueueIds(selectedQueueIds.filter(id => id !== item.id));
                          }
                        }}
                      />
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.name || 'Hiring Manager'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--outline)' }}>{item.email}</div>
                    </td>
                    <td>
                      <div>{item.company || 'N/A'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>{item.role || 'N/A'}</div>
                    </td>
                    <td>
                      {item.job_posting_url ? (
                        <a href={item.job_posting_url} target="_blank" rel="noopener noreferrer"
                           className="btn btn-secondary btn-sm" title="View Job Description">
                          <ExternalLink size={12} /> JD
                        </a>
                      ) : (
                        <span style={{ color: 'var(--outline)', fontSize: '11px' }}>—</span>
                      )}
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
                          <button className="btn btn-primary btn-sm" onClick={() => handlePersonalize(item.id)} disabled={personalizingId === item.id}>
                            {personalizingId === item.id ? (
                              <><Loader2 size={14} className="spin-icon" /> Matching LLM...</>
                            ) : (
                              <><Sparkles size={14} /> Personalize</>
                            )}
                          </button>
                        )}
                        {item.status === 'personalized' && (
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(item.id)} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id}>
                            {approvingId === item.id ? (
                              <><Loader2 size={14} className="spin-icon" /> Approving...</>
                            ) : (
                              <><Check size={14} /> Approve</>
                            )}
                          </button>
                        )}
                        <button className="btn btn-success btn-sm" onClick={() => handleSendNow(item.id)} disabled={sendingId === item.id || approvingId === item.id || rejectingId === item.id}>
                          {sendingId === item.id ? (
                            <><Loader2 size={14} className="spin-icon" /> Sending...</>
                          ) : (
                            <><Send size={12} /> Send Now</>
                          )}
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleReject(item.id)} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id} title="Reject and remove from queue">
                          {rejectingId === item.id ? (
                            <><Loader2 size={14} className="spin-icon" /> Rejecting...</>
                          ) : (
                            <X size={14} color="var(--error)" />
                          )}
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={async () => { if (window.confirm("Are you sure you want to delete this contact entirely?")) { await api.deleteContact(item.id); loadData(); } }} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id} title="Delete contact completely">
                          <Trash2 size={14} color="var(--error)" />
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

      {/* Unverified / Generic Queue Section */}
      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="#d97706" /> Unverified / Generic Queue Approval ({genericQueue.length})
          </h3>
        </div>

        <div style={{ padding: '0 16px' }}>
          {selectedGenericQueueIds.length > 0 && (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '12px 16px', background: 'var(--surface-container-high)', borderRadius: '6px', marginBottom: '12px', marginTop: '12px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>{selectedGenericQueueIds.length} items selected:</span>
              <button className="btn btn-primary btn-sm" onClick={handleBulkApproveGenericQueue}>Approve Selected</button>
              <button className="btn btn-secondary btn-sm" onClick={handleBulkRejectGenericQueue}>Reject Selected</button>
              <button className="btn btn-danger btn-sm" style={{ backgroundColor: 'var(--error)', color: 'white', borderColor: 'var(--error)' }} onClick={handleBulkDeleteGenericQueue}>Delete Selected</button>
            </div>
          )}
        </div>

        {initialLoading ? (
          <SkeletonTable rows={3} columns={5} />
        ) : genericQueue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '20px 0' }}>
            No generic domain contacts currently in queue.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={genericQueue.length > 0 && selectedGenericQueueIds.length === genericQueue.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedGenericQueueIds(genericQueue.map(q => q.id));
                        } else {
                          setSelectedGenericQueueIds([]);
                        }
                      }}
                    />
                  </th>
                  <th>Contact (Guessed)</th>
                  <th>Company &amp; Role</th>
                  <th>JD</th>
                  <th>Status</th>
                  <th>Subject / Preview</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {genericQueue.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedGenericQueueIds.includes(item.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedGenericQueueIds([...selectedGenericQueueIds, item.id]);
                          } else {
                            setSelectedGenericQueueIds(selectedGenericQueueIds.filter(id => id !== item.id));
                          }
                        }}
                      />
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.name || 'Hiring Manager'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--outline)' }}>{item.email}</div>
                    </td>
                    <td>
                      <div>{item.company || 'N/A'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>{item.role || 'N/A'}</div>
                    </td>
                    <td>
                      {item.job_posting_url ? (
                        <a href={item.job_posting_url} target="_blank" rel="noopener noreferrer"
                           className="btn btn-secondary btn-sm" title="View Job Description">
                          <ExternalLink size={12} /> JD
                        </a>
                      ) : (
                        <span style={{ color: 'var(--outline)', fontSize: '11px' }}>—</span>
                      )}
                    </td>
                    <td><span className={`chip chip-${item.status}`}>{item.status}</span></td>
                    <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.subject ? item.subject : <span style={{ color: 'var(--outline)', fontStyle: 'italic' }}>Will use plain company template</span>}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {item.subject && (
                          <button className="btn btn-secondary btn-sm" onClick={() => setSelectedContact(item)}>
                            <Eye size={14} /> Preview
                          </button>
                        )}
                        {item.status === 'generic_new' && (
                          <button className="btn btn-primary btn-sm" onClick={() => handleApprove(item.id)} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id}>
                            {approvingId === item.id ? (
                              <><Loader2 size={14} className="spin-icon" /> Approving...</>
                            ) : (
                              <><Check size={14} /> Approve</>
                            )}
                          </button>
                        )}
                        <button className="btn btn-success btn-sm" onClick={() => handleSendNow(item.id)} disabled={sendingId === item.id || approvingId === item.id || rejectingId === item.id}>
                          {sendingId === item.id ? (
                            <><Loader2 size={14} className="spin-icon" /> Sending...</>
                          ) : (
                            <><Send size={12} /> Send Now</>
                          )}
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleReject(item.id)} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id} title="Reject and remove from queue">
                          {rejectingId === item.id ? (
                            <><Loader2 size={14} className="spin-icon" /> Rejecting...</>
                          ) : (
                            <X size={14} color="var(--error)" />
                          )}
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={async () => { if (window.confirm("Are you sure you want to delete this contact entirely?")) { await api.deleteContact(item.id); loadData(); } }} disabled={approvingId === item.id || rejectingId === item.id || sendingId === item.id} title="Delete contact completely">
                          <Trash2 size={14} color="var(--error)" />
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
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <h3 className="card-title">Contacts Directory ({contacts.length})</h3>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {['all', 'new', 'personalized', 'queued', 'sent', 'replied', 'bounced', 'rejected'].map((st) => (
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

        <div style={{ padding: '0 16px' }}>
          {selectedContactIds.length > 0 && (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '12px 16px', background: 'var(--surface-container-high)', borderRadius: '6px', marginBottom: '12px', marginTop: '12px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>{selectedContactIds.length} contacts selected:</span>
              <button className="btn btn-danger btn-sm" style={{ backgroundColor: 'var(--error)', color: 'white', borderColor: 'var(--error)' }} onClick={handleBulkDeleteContacts}>Delete Selected Contacts</button>
            </div>
          )}
        </div>

        {initialLoading ? (
          <SkeletonTable rows={5} columns={6} />
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={filteredContacts.length > 0 && selectedContactIds.length === filteredContacts.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedContactIds(filteredContacts.map(c => c.id));
                        } else {
                          setSelectedContactIds([]);
                        }
                      }}
                    />
                  </th>
                  <th>Recipient</th>
                  <th>Company</th>
                  <th>Role</th>
                  <th>JD Link</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredContacts.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedContactIds.includes(c.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedContactIds([...selectedContactIds, c.id]);
                          } else {
                            setSelectedContactIds(selectedContactIds.filter(id => id !== c.id));
                          }
                        }}
                      />
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{c.name || 'Hiring Manager'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--outline)' }}>{c.email}</div>
                    </td>
                    <td>{c.company || 'N/A'}</td>
                    <td>{c.role || 'N/A'}</td>
                    <td>
                      {c.job_posting_url ? (
                        <a
                          href={c.job_posting_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary btn-sm"
                          title={c.job_posting_url}
                        >
                          <ExternalLink size={12} /> JD
                        </a>
                      ) : (
                        <span style={{ color: 'var(--outline)', fontSize: '11px' }}>—</span>
                      )}
                    </td>
                    <td style={{ fontSize: '12px' }}>{c.source || 'manual'}</td>
                    <td><span className={`chip chip-${c.status}`}>{c.status}</span></td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {c.body && (
                          <button className="btn btn-secondary btn-sm" onClick={() => setSelectedContact(c)}>
                            <Eye size={14} />
                          </button>
                        )}
                        <button className="btn btn-secondary btn-sm" onClick={async () => { if (window.confirm("Are you sure you want to delete this contact?")) { await api.deleteContact(c.id); loadData(); } }}>
                          <Trash2 size={14} color="var(--error)" />
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
              {selectedContact.job_posting_url && (
                <div style={{ marginTop: '4px' }}>
                  <strong>JD:</strong>{' '}
                  <a
                    href={selectedContact.job_posting_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary)', textDecoration: 'underline' }}
                  >
                    View Job Description ↗
                  </a>
                </div>
              )}
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

            {['new', 'personalized', 'queued'].includes(selectedContact.status) && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                <button className="btn btn-secondary" onClick={() => setSelectedContact(null)}>Cancel</button>
                <button className="btn btn-success" onClick={async () => {
                  const id = selectedContact.id;
                  setSelectedContact(null);
                  await handleSendNow(id);
                }} disabled={sendingId === selectedContact.id}>
                  {sendingId === selectedContact.id ? (
                    <><Loader2 size={16} className="spin-icon" /> Sending Email...</>
                  ) : (
                    <><Send size={16} /> Send Email Now</>
                  )}
                </button>
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
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }} disabled={addingContact}>
                {addingContact ? (
                  <><Loader2 size={16} className="spin-icon" /> Saving Contact...</>
                ) : (
                  'Save Contact'
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
