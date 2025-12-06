import { useState, useEffect, useRef } from "react";

const BASE_URL = "https://liftable-actionable-joeann.ngrok-free.dev";
const COMMAND_URL = `${BASE_URL}/command`;
const CHAT_URL = `${BASE_URL}/chat`;

// Decide if this is an automation command or just chat
const automationPhrases = [
  "open chrome and go to gmail",
  // add more exact phrases here if needed:
  // "open notepad and write hello world",
  // "take a screenshot and save it to desktop",
];

const isAutomationCommand = (text) => {
  const normalized = text.trim().toLowerCase();
  return automationPhrases.includes(normalized);
};

function App() {
  const [messages, setMessages] = useState([
    {
      from: "jarvis",
      text: "Boot sequence initiated…",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showIntro, setShowIntro] = useState(true);
  const messagesEndRef = useRef(null);

  // Intro sequence: messages + hide overlay
  useEffect(() => {
    const t1 = setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          from: "jarvis",
          text:
            "Jarvis online. Give me a natural language command and I’ll control your desktop.",
          timestamp: new Date(),
        },
      ]);
    }, 900);

    const t2 = setTimeout(() => {
      setShowIntro(false);
    }, 2200);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  // Auto-scroll on new messages / loading
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Ctrl/Cmd + Space → mic
  useEffect(() => {
    const handleGlobalKey = (e) => {
      const isCtrlOrCmd = e.ctrlKey || e.metaKey;
      if (isCtrlOrCmd && e.code === "Space") {
        e.preventDefault();
        handleVoiceClick();
      }
    };

    window.addEventListener("keydown", handleGlobalKey);
    return () => window.removeEventListener("keydown", handleGlobalKey);
  }, []);

  const addJarvisMessage = (text) => {
    setMessages((prev) => [
      ...prev,
      { from: "jarvis", text, timestamp: new Date() },
    ]);
  };

  // Personality mode for greetings / help / thanks
  const tryHandleLocally = (userText) => {
    const t = userText.trim().toLowerCase();

    if (["hi", "hey", "hello"].includes(t) || t.startsWith("hi jarvis")) {
      addJarvisMessage(
        "Hey! All systems are green. Try something like “Open Chrome and go to Gmail.”"
      );
      return true;
    }

    if (t.includes("who are you") || t.includes("what are you")) {
      addJarvisMessage(
        "I’m Jarvis – a thin AI layer turning your sentences into desktop actions. Think of me as a friendly OS overlord."
      );
      return true;
    }

    if (t.includes("what can you do") || t.includes("help")) {
      addJarvisMessage(
        "I can orchestrate apps and scripts. Examples:\n• Open Chrome and go to Gmail\n• Open Notepad and write Hello World\n• Take a screenshot and save it to Desktop"
      );
      return true;
    }

    if (t.startsWith("thank") || t.includes("thanks")) {
      addJarvisMessage(
        "Anytime. Automation is kind of my entire personality."
      );
      return true;
    }

    return false;
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userText = input.trim();
    setInput("");

    const now = new Date();

    setMessages((prev) => [
      ...prev,
      { from: "you", text: userText, timestamp: now },
    ]);

    // Handle small talk locally
    if (tryHandleLocally(userText)) return;

    setIsLoading(true);

    try {
      // 🔥 Decide which backend endpoint to hit
      const endpoint = isAutomationCommand(userText)
        ? COMMAND_URL
        : CHAT_URL;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: userText }),
      });

      const data = await res.json();
      console.log("Response JSON:", data);

      const replyTime = new Date();
      const jarvisMsgs = [];

      const primaryText =
        (typeof data === "string" && data) ||
        data.text ||
        data.message ||
        data.result ||
        data.spoken_response;

      if (primaryText) {
        jarvisMsgs.push({
          from: "jarvis",
          text: primaryText,
          timestamp: replyTime,
        });
      }

      const logs = data.logs || data.steps || data.plan;
      if (Array.isArray(logs)) {
        logs.forEach((log) => {
          jarvisMsgs.push({
            from: "jarvis",
            text: String(log),
            timestamp: new Date(),
          });
        });
      }

      if (jarvisMsgs.length === 0) {
        jarvisMsgs.push({
          from: "jarvis",
          text:
            "Backend responded in an unexpected format:\n" +
            JSON.stringify(data),
          timestamp: replyTime,
        });
      }

      setMessages((prev) => [...prev, ...jarvisMsgs]);

      if (primaryText && "speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(primaryText);
        window.speechSynthesis.speak(utterance);
      }
    } catch (err) {
      console.error("Fetch error:", err);
      addJarvisMessage(
        "I lost connection to my automation core. Is the backend still running?"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceClick = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      addJarvisMessage(
        "🎙️ This browser doesn’t support voice capture. Try desktop Chrome or Edge."
      );
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsRecording(true);

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log("Voice input:", transcript);
        setInput(transcript);
        setTimeout(() => {
          handleSend();
        }, 250);
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsRecording(false);
        addJarvisMessage("🎙️ Voice hiccup: " + event.error);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
    } catch (err) {
      console.error("Voice init error:", err);
      setIsRecording(false);
      addJarvisMessage(
        "🎙️ I tried to start listening but something went wrong. Maybe refresh?"
      );
    }
  };

  const formatTime = (date) => {
    if (!date) return "";
    try {
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  return (
    <div className="min-h-screen jarvis-bg text-slate-100 flex items-center justify-center px-3">
      {/* Fullscreen boot overlay */}
      {showIntro && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/85 z-40">
          {/* rotating HUD circles */}
          <div className="absolute w-72 h-72 rounded-full border border-emerald-400/40 hud-ring-slow" />
          <div className="absolute w-96 h-96 rounded-full border border-cyan-400/30 hud-ring-reverse" />
          <div className="absolute w-56 h-56 rounded-full border border-emerald-300/40 hud-ring-pulse" />

          <div className="border border-emerald-400/60 bg-slate-950/95 rounded-3xl px-8 py-6 max-w-lg w-[90%] shadow-[0_0_40px_rgba(16,185,129,0.7)] intro-panel relative">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 border border-emerald-400/60 flex items-center justify-center text-emerald-300 text-xl">
                J
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-emerald-300/80">
                  Stark Systems
                </p>
                <h1 className="text-lg font-semibold">Initializing Jarvis</h1>
              </div>
            </div>
            <div className="text-[12px] font-mono text-emerald-100/90 space-y-1">
              <p className="jarvis-line">[ OK ] Boot sequence started…</p>
              <p className="jarvis-line delay-1">
                [ OK ] Neural planner linked to automation core…
              </p>
              <p className="jarvis-line delay-2">
                [ OK ] Desktop control bridge online.
              </p>
            </div>
            <p className="text-[11px] text-slate-400 mt-4">
              Tip: Press <span className="text-emerald-300">Ctrl+Space</span> to
              talk to Jarvis at any time.
            </p>
          </div>
        </div>
      )}

      {/* HUD background rings (always visible, subtle) */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute left-[-120px] top-10 w-72 h-72 rounded-full border border-emerald-500/30 hud-ring-slow" />
        <div className="absolute right-[-140px] bottom-0 w-80 h-80 rounded-full border border-cyan-400/25 hud-ring-reverse" />
        <div className="absolute right-10 top-10 w-40 h-40 rounded-full border border-emerald-300/25 hud-ring-pulse" />
      </div>

      {/* Side HUD panels (metrics, etc.) */}
      <div className="hidden lg:flex flex-col gap-3 absolute left-4 top-10 text-[10px] text-emerald-100/70 font-mono z-10">
        <div className="hud-panel">
          <div className="hud-panel-title">SYSTEM STATUS</div>
          <div>CPU LINK: STABLE</div>
          <div>AUTOMATION CORE: ONLINE</div>
          <div>VOICE CHANNEL: ACTIVE</div>
        </div>
        <div className="hud-panel">
          <div className="hud-panel-title">RECENT MODES</div>
          <div>VOICE COMMANDS</div>
          <div>PLANNING SCRIPTS</div>
          <div>DESKTOP CONTROL</div>
        </div>
      </div>

      <div className="hidden lg:flex flex-col gap-3 absolute right-4 bottom-10 text-[10px] text-emerald-100/70 font-mono z-10 items-end">
        <div className="hud-panel hud-panel-right">
          <div className="hud-panel-title text-right">HUD METRICS</div>
          <div>LATENCY: LOW</div>
          <div>OS LINK: SECURE</div>
          <div>AI CORE: GPT-POWERED</div>
        </div>
      </div>

      {/* Main console */}
      <div className="app-shell w-full max-w-3xl h-[90vh] bg-slate-950/85 border border-emerald-500/40 rounded-3xl flex flex-col overflow-hidden shadow-[0_0_50px_rgba(16,185,129,0.55)] backdrop-blur relative z-20">
        {/* inner grid */}
        <div className="pointer-events-none absolute inset-0 jarvis-grid rounded-3xl opacity-40" />

        {/* Header */}
        <header className="px-5 py-4 border-b border-emerald-500/30 bg-slate-950/80 relative z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-2xl bg-emerald-500/20 border border-emerald-400/70 flex items-center justify-center text-emerald-200 text-lg">
                J
              </div>
              <div>
                <h1 className="text-base font-semibold tracking-wide">
                  Jarvis Control Console
                </h1>
                <p className="text-[11px] text-emerald-200/80">
                  Natural language → system automation.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="px-2 py-1 rounded-full border border-emerald-400/60 text-emerald-200 inline-flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Online
              </span>
            </div>
          </div>

          {/* Voice HUD + hint */}
          <div className="mt-2 flex items-center gap-3 text-[11px] text-emerald-100/80">
            <div className="relative w-8 h-8 flex items-center justify-center">
              {/* circular hologram around mic when recording */}
              <div
                className={`absolute inset-0 rounded-full mic-ring ${
                  isRecording ? "mic-ring-active" : "mic-ring-idle"
                }`}
              />
              <div className="w-3 h-3 rounded-full bg-emerald-300/90 shadow-[0_0_12px_rgba(16,185,129,0.9)]" />
            </div>
            <span className="truncate">
              {isRecording
                ? "Listening… say a command clearly."
                : "Press Ctrl+Space or tap the mic to talk to Jarvis."}
            </span>
          </div>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto px-4 py-3 space-y-3 relative z-10">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${
                m.from === "you" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`message-bubble max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-lg ${
                  m.from === "you"
                    ? "bg-emerald-600 text-white rounded-br-sm"
                    : "bg-slate-900/90 text-emerald-50 rounded-bl-sm border border-emerald-500/25 whitespace-pre-line"
                }`}
              >
                <div>{m.text}</div>
                <div
                  className={`mt-1 text-[10px] ${
                    m.from === "you"
                      ? "text-emerald-100/80 text-right"
                      : "text-emerald-200/70 text-left"
                  }`}
                >
                  {m.from === "you" ? "You" : "Jarvis"} ·{" "}
                  {formatTime(m.timestamp)}
                </div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="message-bubble max-w-[60%] rounded-2xl px-3 py-2 text-xs bg-slate-900/90 text-emerald-100 rounded-bl-sm border border-emerald-500/30 flex items-center gap-2 shadow-md">
                <span className="inline-flex gap-1 items-center">
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </span>
                <span className="text-[11px]">
                  Jarvis is planning your automation…
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* Input bar */}
        <footer className="border-t border-emerald-500/30 px-3 py-2 bg-slate-950/85 relative z-10">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleVoiceClick}
              className={`shrink-0 w-9 h-9 rounded-full border flex items-center justify-center text-xs shadow-md ${
                isRecording
                  ? "border-emerald-400 bg-emerald-500/20 text-emerald-200 animate-pulse"
                  : "border-emerald-500/50 bg-slate-900/80 text-emerald-200"
              }`}
            >
              🎙️
            </button>
            <input
              className="flex-1 bg-slate-900/80 border border-emerald-500/40 rounded-xl px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-emerald-400 focus:border-emerald-400 placeholder:text-emerald-200/40"
              placeholder="Tell Jarvis what to do..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isLoading}
              className="shrink-0 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-xl shadow-md transition-transform active:scale-[0.96]"
            >
              Send
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
