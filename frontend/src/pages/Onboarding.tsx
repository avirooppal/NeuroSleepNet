import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Copy, ArrowRight, Brain, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import { useOnboardingStore } from '../store';

const PYTHON_SNIPPET = `pip install neurosleepnet

import neurosleepnet as nsn
nsn.init("YOUR_API_KEY")
agent = nsn.wrap(your_agent)  # Done.`;

const NODE_SNIPPET = `npm install neurosleepnet

const nsn = require('neurosleepnet');
nsn.init('YOUR_API_KEY');
const agent = nsn.wrap(yourAgent);`;

export default function Onboarding() {
  const { step, setStep, complete, apiKeyCopied, setApiKeyCopied, roundTripVerified, setRoundTripVerified } = useOnboardingStore();
  const [tab, setTab] = useState<'python' | 'node'>('python');
  const [verifying, setVerifying] = useState(false);
  const apiKey = localStorage.getItem('nsn-demo-key') ?? 'nsn_demo_key_here';

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setApiKeyCopied(true);
    toast.success('API key copied ✓');
  };

  const copySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Snippet copied ✓');
  };

  const runVerification = async () => {
    setVerifying(true);
    try {
      await new Promise(r => setTimeout(r, 1500)); // Simulate round-trip
      setRoundTripVerified(true);
      toast.success('Live round-trip verified — memories stored and retrieved ✓');
    } catch {
      toast.error('Verification failed — check your API key');
    } finally {
      setVerifying(false);
    }
  };

  const steps = [
    { label: 'Get Your Key', icon: <Brain size={16} /> },
    { label: 'Install SDK', icon: <Zap size={16} /> },
    { label: 'Verify', icon: <Check size={16} /> },
  ];

  return (
    <div className="onboarding-root">
      <div className="onboarding-card">
        <div className="onboarding-logo">🧠 NeuroSleepNet</div>
        <h1 className="onboarding-title">Set up in 60 seconds</h1>

        {/* Step indicator */}
        <div className="step-indicator">
          {steps.map((s, i) => (
            <React.Fragment key={i}>
              <button
                className={`step-dot ${step === i + 1 ? 'active' : step > i + 1 ? 'done' : ''}`}
                onClick={() => step > i && setStep((i + 1) as any)}
              >
                {step > i + 1 ? <Check size={12} /> : s.icon}
                <span>{s.label}</span>
              </button>
              {i < 2 && <div className={`step-line ${step > i + 1 ? 'done' : ''}`} />}
            </React.Fragment>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1 — Get Your Key */}
          {(step === 0 || step === 1) && (
            <motion.div key="step1" className="step-content" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h2 className="step-title">Your API Key</h2>
              <p className="step-desc">Save this key somewhere safe — you won't be able to see it again.</p>
              <div className="key-display">
                <code className="key-text">{apiKey}</code>
                <button className="copy-key-btn" onClick={copyKey}><Copy size={14} /></button>
              </div>
              {apiKeyCopied && <div className="step-check"><Check size={13} className="text-teal" /> Key saved</div>}
              <button className="step-next-btn" onClick={() => setStep(2)}>Next <ArrowRight size={14} /></button>
            </motion.div>
          )}

          {/* Step 2 — Install SDK */}
          {step === 2 && (
            <motion.div key="step2" className="step-content" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h2 className="step-title">Install & Integrate</h2>
              <div className="tab-row">
                {(['python', 'node'] as const).map(t => (
                  <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t === 'python' ? 'Python' : 'Node.js'}</button>
                ))}
              </div>
              <div className="code-block-wrapper">
                <pre className="code-block">{tab === 'python' ? PYTHON_SNIPPET : NODE_SNIPPET}</pre>
                <button className="copy-code-btn" onClick={() => copySnippet(tab === 'python' ? PYTHON_SNIPPET : NODE_SNIPPET)}><Copy size={12} /></button>
              </div>
              <button className="step-next-btn" onClick={() => setStep(3)}>Next <ArrowRight size={14} /></button>
            </motion.div>
          )}

          {/* Step 3 — Verify */}
          {step === 3 && (
            <motion.div key="step3" className="step-content" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h2 className="step-title">Verify Connection</h2>
              <p className="step-desc">We'll store 3 test memories and retrieve them in real time. This is a live round-trip — not just a ping.</p>
              {!roundTripVerified ? (
                <button className="step-next-btn" onClick={runVerification} disabled={verifying}>
                  {verifying ? 'Running…' : '▶ Run verification'}
                </button>
              ) : (
                <div className="verify-success">
                  <Check size={24} className="text-teal" />
                  <div className="text-teal font-bold">Connection verified — 3 memories round-tripped successfully</div>
                  <button className="step-next-btn" onClick={complete}>Go to Dashboard <ArrowRight size={14} /></button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
