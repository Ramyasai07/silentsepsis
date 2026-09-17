import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, ShieldCheck } from 'lucide-react';

function buildAnswer(patient) {
  const top = patient.features[0];
  const lines = [
    `${patient.name}, room ${patient.room} - risk score ${patient.risk ?? 'unavailable'}/100 (${patient.status}).`,
  ];
  if (top) {
    lines.push(`Strongest contributing factor: ${top.name.toLowerCase()} at ${top.contribution}.`);
  }
  lines.push(patient.explanation);
  if (patient.timeToIntervention) {
    lines.push(`Estimated time to intervention: ${patient.timeToIntervention}.`);
  }
  return lines.join(' ');
}

const NOT_FOUND = "I can only answer using data the model has actually computed for a monitored patient. I couldn't match that to anyone on the ward. Try a name or room number from the current list.";

export function ChatWidget({ patients = [] }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Ask me about any monitored patient by name or room. I will read back exactly what the model has flagged, nothing more.' },
  ]);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  function findPatient(query) {
    const q = query.toLowerCase();
    return patients.find((p) =>
      p.name.toLowerCase().includes(q) || p.room.toLowerCase().includes(q)
    );
  }

  function ask(query) {
    const text = query.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');

    const patient = findPatient(text);
    const reply = patient ? buildAnswer(patient) : NOT_FOUND;
    setMessages((m) => [...m, { role: 'assistant', text: reply, grounded: !!patient }]);
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-80 h-[440px] rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark shadow-2xl flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-pastel-brand text-white shrink-0">
            <div className="flex items-center gap-2">
              <ShieldCheck size={15} aria-hidden="true" />
              <span className="text-[13px] font-semibold">Patient lookup</span>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close" className="opacity-80 hover:opacity-100">
              <X size={16} />
            </button>
          </div>

          <p className="px-4 pt-2.5 pb-1.5 text-[10.5px] text-pastel-sub dark:text-pastel-subDark leading-snug border-b border-pastel-bg dark:border-pastel-borderDark">
            Answers are read directly from monitored data - not free-form AI generation.
          </p>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3.5 py-3 space-y-2.5">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-2xl text-[12.5px] leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-pastel-brand text-white rounded-br-sm'
                      : 'bg-pastel-bg dark:bg-white/5 text-pastel-ink dark:text-pastel-inkDark rounded-bl-sm'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-1.5 px-3 pb-2 flex-wrap">
            {patients.slice(0, 3).map((p) => (
              <button
                key={p.id}
                onClick={() => ask(p.name)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-pastel-bg dark:bg-white/5 text-pastel-sub dark:text-pastel-subDark hover:bg-pastel-brandLight dark:hover:bg-pastel-brandLightDark hover:text-pastel-brand transition-colors"
              >
                {p.name}
              </button>
            ))}
          </div>

          <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex items-center gap-2 p-2.5 border-t border-pastel-bg dark:border-pastel-borderDark shrink-0">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Name or room number..."
              className="flex-1 h-9 px-3 rounded-full bg-pastel-bg dark:bg-white/5 text-[12.5px] text-pastel-ink dark:text-pastel-inkDark outline-none placeholder:text-pastel-sub/70"
            />
            <button
              type="submit"
              className="h-9 w-9 rounded-full bg-pastel-brand text-white flex items-center justify-center shrink-0 disabled:opacity-50"
              disabled={!input.trim()}
              aria-label="Send"
            >
              <Send size={14} aria-hidden="true" />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-50 h-[52px] w-[52px] rounded-full bg-pastel-brand text-white shadow-lg flex items-center justify-center hover:scale-105 transition-transform"
        aria-label={open ? 'Close patient lookup' : 'Open patient lookup'}
      >
        {open ? <X size={20} /> : <MessageCircle size={20} />}
      </button>
    </>
  );
}
