import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Trash2, Clock, ToggleLeft, ToggleRight, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { usePreferencesStore } from '../store';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';

export default function Settings() {
  const { piiDetection, setPiiDetection, memoryTtlDays, setMemoryTtlDays } = usePreferencesStore();
  const [showPiiWarning, setShowPiiWarning] = useState(false);
  const [dangerZoneText, setDangerZoneText] = useState('');
  const [ttlInput, setTtlInput] = useState<string>(memoryTtlDays ? String(memoryTtlDays) : '');

  const handlePiiToggle = () => {
    if (piiDetection) {
      setShowPiiWarning(true); // Show warning before disabling
    } else {
      setPiiDetection(true);
      toast.success('PII detection enabled');
    }
  };

  const confirmDisablePii = () => {
    setPiiDetection(false);
    setShowPiiWarning(false);
    toast('PII detection disabled — store data responsibly.', { icon: '⚠️' });
  };

  const saveTtl = () => {
    const days = ttlInput ? parseInt(ttlInput) : null;
    setMemoryTtlDays(days);
    toast.success(days ? `Memory TTL set to ${days} days` : 'Memory TTL cleared (no expiry)');
  };

  const handleDeleteAccount = async () => {
    if (dangerZoneText !== 'delete my account') return;
    toast.error('Account deletion is irreversible — contact support@nsn.ai for help.');
  };

  return (
    <div className="page-root">
      <h1 className="dashboard-title">Settings</h1>

      {/* PII Detection */}
      <div className="settings-section">
        <div className="settings-section-header">
          <Shield size={16} className="text-teal" />
          <span>PII Detection</span>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Detect & redact personal information</div>
            <div className="settings-desc text-muted text-xs">Emails, phones, SSNs, credit cards are automatically redacted before storage. Default ON.</div>
          </div>
          <button onClick={handlePiiToggle} className="toggle-btn">
            {piiDetection ? <ToggleRight size={28} className="text-teal" /> : <ToggleLeft size={28} className="text-muted" />}
          </button>
        </div>
      </div>

      {/* Memory TTL */}
      <div className="settings-section">
        <div className="settings-section-header"><Clock size={16} className="text-teal" /><span>Memory TTL</span></div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Auto-delete memories after N days</div>
            <div className="settings-desc text-muted text-xs">Hard deletion from storage. Required for GDPR and data retention policies. Leave blank for no expiry.</div>
          </div>
          <div className="flex gap-2 items-center">
            <input className="memory-search-input w-24" type="number" placeholder="days" value={ttlInput} onChange={e => setTtlInput(e.target.value)} />
            <button className="create-btn" onClick={saveTtl}>Save</button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="settings-section danger">
        <div className="settings-section-header text-red"><Trash2 size={16} /><span>Danger Zone</span></div>
        <div className="settings-label">Delete account and all data</div>
        <div className="settings-desc text-muted text-xs mb-3">This is irreversible. All memories, projects, and API keys will be permanently deleted.</div>
        <input
          className="memory-search-input"
          placeholder='Type "delete my account" to confirm'
          value={dangerZoneText}
          onChange={e => setDangerZoneText(e.target.value)}
        />
        <button
          className="danger-btn mt-2"
          onClick={handleDeleteAccount}
          disabled={dangerZoneText !== 'delete my account'}
        >
          Delete everything
        </button>
      </div>

      {/* PII Warning Modal */}
      <AnimatePresence>
        {showPiiWarning && (
          <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="modal-card" initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }}>
              <div className="modal-icon"><AlertTriangle size={24} className="text-amber" /></div>
              <h2 className="modal-title">Disable PII Detection?</h2>
              <p className="modal-body">
                Disabling PII detection means raw personal data (emails, phone numbers, SSNs) may be stored in your memory store. This is a <strong>conscious opt-out</strong> — not the default.
              </p>
              <div className="modal-actions">
                <button className="cancel-btn" onClick={() => setShowPiiWarning(false)}>Keep it enabled</button>
                <button className="danger-btn" onClick={confirmDisablePii}>Yes, disable PII detection</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
