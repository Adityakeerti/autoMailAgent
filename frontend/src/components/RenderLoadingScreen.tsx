import React, { useState, useEffect, useRef } from 'react';
import { Cpu, Zap, Award, Sparkles, Gamepad2, AlertCircle } from 'lucide-react';

interface RenderLoadingScreenProps {
  onFinished: () => void;
  checkStatus: () => Promise<boolean>;
}

interface GameObject {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  type: 'job' | 'lead' | 'spam' | 'recruiter';
  label: string;
  size: number;
}

export const RenderLoadingScreen: React.FC<RenderLoadingScreenProps> = ({ onFinished, checkStatus }) => {
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() => {
    return parseInt(localStorage.getItem('outreach_game_highscore') || '0');
  });
  const [objects, setObjects] = useState<GameObject[]>([]);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState('Initiating spin-up request...');
  const [hasStarted, setHasStarted] = useState(false);
  const [isWakingUp, setIsWakingUp] = useState(true);
  const gameAreaRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  // Status message rotation based on estimated boot time
  useEffect(() => {
    const messages = [
      { p: 0, m: 'Sending wake-up signal to Render Web Service...' },
      { p: 10, m: 'FastAPI container starting up from cold storage...' },
      { p: 25, m: 'Mounting virtual volumes and SQLite context database...' },
      { p: 40, m: 'Loading LLM templates and dynamic outreach scripts...' },
      { p: 60, m: 'Warming up Playwright browser selection manager...' },
      { p: 80, m: 'Initializing AI filter scoring weights...' },
      { p: 95, m: 'Awaiting final server confirmation handshake...' },
    ];

    const current = messages.reverse().find(entry => progress >= entry.p);
    if (current) {
      setStatusMsg(current.m);
    }
  }, [progress]);

  // Simulate progress bar movement over 50s (typical Render free tier sleep boot time)
  useEffect(() => {
    let timer: any;
    if (isWakingUp) {
      timer = setInterval(() => {
        setProgress(prev => {
          if (prev >= 98) return prev;
          // Curve: starts fast, slows down at the end until actually connected
          const step = prev < 50 ? 2 : prev < 80 ? 1 : 0.2;
          return Math.min(99, prev + step);
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isWakingUp]);

  // Active polling to check if the server woke up
  useEffect(() => {
    let active = true;
    const pollServer = async () => {
      while (active && isWakingUp) {
        try {
          const alive = await checkStatus();
          if (alive) {
            setProgress(100);
            setIsWakingUp(false);
            setTimeout(() => {
              onFinished();
            }, 1000);
            break;
          }
        } catch (e) {
          // Keep polling silently
        }
        // Poll every 3 seconds
        await new Promise(r => setTimeout(r, 3000));
      }
    };
    pollServer();
    return () => { active = false; };
  }, [checkStatus, onFinished, isWakingUp]);

  // Game loop: spawning and moving objects
  useEffect(() => {
    if (!hasStarted || !isWakingUp) return;

    const spawnTypes: Array<GameObject['type']> = ['job', 'lead', 'spam', 'recruiter'];
    const labels = {
      job: '💼 Offer',
      lead: '🎯 Lead',
      spam: '🚨 Spam',
      recruiter: '🗣️ Recruiter'
    };
    const sizes = {
      job: 60,
      lead: 50,
      spam: 45,
      recruiter: 70
    };

    // Spawn an object every 1.5 seconds
    const spawner = setInterval(() => {
      if (!gameAreaRef.current) return;
      const width = gameAreaRef.current.clientWidth || 600;
      const type = spawnTypes[Math.floor(Math.random() * spawnTypes.length)];

      const newObj: GameObject = {
        id: nextId.current++,
        x: Math.random() * (width - 80) + 10,
        y: -80, // Spawn just off-screen
        vx: (Math.random() - 0.5) * 4,
        vy: Math.random() * 2 + 1.5,
        type,
        label: labels[type],
        size: sizes[type]
      };

      setObjects(prev => [...prev, newObj]);
    }, 1200);

    // Physics update frame loop
    let animFrame: number;
    const updatePhysics = () => {
      if (!gameAreaRef.current) return;
      const height = gameAreaRef.current.clientHeight || 400;
      const width = gameAreaRef.current.clientWidth || 600;

      setObjects(prev => {
        return prev
          .map(obj => {
            // Apply velocities
            let newX = obj.x + obj.vx;
            let newY = obj.y + obj.vy;
            let newVx = obj.vx;

            // Bounce horizontal walls
            if (newX < 0 || newX + obj.size > width) {
              newVx = -obj.vx;
              newX = Math.max(0, Math.min(newX, width - obj.size));
            }

            return {
              ...obj,
              x: newX,
              y: newY,
              vx: newVx
            };
          })
          // Filter out objects that fall completely below the visible screen
          .filter(obj => obj.y < height + 50);
      });

      animFrame = requestAnimationFrame(updatePhysics);
    };

    animFrame = requestAnimationFrame(updatePhysics);

    return () => {
      clearInterval(spawner);
      cancelAnimationFrame(animFrame);
    };
  }, [hasStarted, isWakingUp]);

  const handleObjectClick = (obj: GameObject) => {
    let points = 0;
    if (obj.type === 'job') points = 100;
    else if (obj.type === 'lead') points = 50;
    else if (obj.type === 'recruiter') points = 250;
    else if (obj.type === 'spam') points = -100;

    setScore(prev => {
      const next = Math.max(0, prev + points);
      if (next > highScore) {
        setHighScore(next);
        localStorage.setItem('outreach_game_highscore', String(next));
      }
      return next;
    });

    // Remove clicked object
    setObjects(prev => prev.filter(o => o.id !== obj.id));
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', background: 'radial-gradient(circle at center, #0f172a, #020617)',
      color: '#f8fafc', fontFamily: 'system-ui, sans-serif', padding: 20, overflow: 'hidden'
    }}>
      <div style={{ maxWidth: 800, width: '100%', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Game Title Header */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 8 }}>
            <Cpu size={28} className={isWakingUp ? 'spin' : ''} style={{ color: '#6366f1' }} />
            <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, letterSpacing: '0.05em', color: '#818cf8' }}>
              GETNEWJOB SERVER SPIN-UP
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
            We're starting up the Render free tier server. Warm up your mouse!
          </p>
        </div>

        {/* Server Status Progress Bar */}
        <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: '#a5b4fc', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Zap size={14} /> {statusMsg}
            </span>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#818cf8' }}>{Math.floor(progress)}%</span>
          </div>
          
          {/* Progress outer */}
          <div style={{ background: '#0f172a', height: 16, borderRadius: 8, overflow: 'hidden', padding: 2 }}>
            <div style={{
              background: 'linear-gradient(90deg, #4f46e5, #818cf8)',
              height: '100%',
              width: `${progress}%`,
              borderRadius: 6,
              transition: 'width 0.4s ease'
            }} />
          </div>
          
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 10, fontSize: 11, color: '#64748b' }}>
            <AlertCircle size={12} />
            <span>Render servers fall asleep after 15 minutes of inactivity. Initial boot takes 40-60 seconds.</span>
          </div>
        </div>

        {/* Arcade Cabinet Box */}
        <div style={{
          background: '#1e293b', border: '3px solid #4f46e5', borderRadius: 16,
          boxShadow: '0 0 20px rgba(79, 70, 229, 0.4)', overflow: 'hidden', display: 'flex', flexDirection: 'column'
        }}>
          {/* Scoreboard */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 20px', background: '#0f172a', borderBottom: '2px solid #334155'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Gamepad2 size={16} color="#818cf8" />
              <span style={{ fontSize: 13, color: '#94a3b8', fontWeight: 600 }}>OUTREACH CLICKER</span>
            </div>
            
            <div style={{ display: 'flex', gap: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={14} color="#facc15" />
                <span style={{ fontSize: 14, fontWeight: 700 }}>Score: <span style={{ color: '#facc15' }}>{score}</span></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Award size={14} color="#34d399" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#94a3b8' }}>High: <span style={{ color: '#34d399' }}>{highScore}</span></span>
              </div>
            </div>
          </div>

          {/* Game Window Panel */}
          <div
            ref={gameAreaRef}
            style={{
              height: 380, position: 'relative', background: '#0b0f19',
              cursor: hasStarted ? 'crosshair' : 'default', display: 'flex',
              alignItems: 'center', justifyContent: 'center', overflow: 'hidden'
            }}
          >
            {!hasStarted ? (
              <div style={{ textAlign: 'center', zIndex: 10, maxWidth: 300, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <h3 style={{ margin: 0, fontSize: 18, color: '#f8fafc' }}>Outreach Mini-Game</h3>
                <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Click job offers, recruiter chat requests, and leads to warm up the pipelines. Avoid catching spam!
                </p>
                <button
                  className="btn btn-primary"
                  onClick={() => setHasStarted(true)}
                  style={{ alignSelf: 'center', padding: '8px 24px', fontSize: 13, fontWeight: 700, borderRadius: 8 }}
                >
                  Start Warmup Game
                </button>
              </div>
            ) : !isWakingUp ? (
              <div style={{ textAlign: 'center', zIndex: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <h3 style={{ margin: 0, fontSize: 22, color: '#34d399', fontWeight: 800 }}>⚡ SERVER CONNECTED!</h3>
                <p style={{ margin: 0, fontSize: 13, color: '#94a3b8' }}>
                  Handshake successful. Launching GetNewJob dashboard...
                </p>
              </div>
            ) : objects.length === 0 ? (
              <p style={{ color: '#475569', fontSize: 12, userSelect: 'none' }}>Catching outreach streams...</p>
            ) : (
              objects.map(obj => (
                <button
                  key={obj.id}
                  onClick={() => handleObjectClick(obj)}
                  style={{
                    position: 'absolute',
                    left: obj.x,
                    top: obj.y,
                    width: obj.size,
                    height: obj.size,
                    borderRadius: '50%',
                    border: `2px solid ${
                      obj.type === 'job' ? '#10b981' :
                      obj.type === 'lead' ? '#3b82f6' :
                      obj.type === 'recruiter' ? '#8b5cf6' : '#ef4444'
                    }`,
                    background: `${
                      obj.type === 'job' ? 'rgba(16, 185, 129, 0.2)' :
                      obj.type === 'lead' ? 'rgba(59, 130, 246, 0.2)' :
                      obj.type === 'recruiter' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(239, 68, 68, 0.2)'
                    }`,
                    color: '#f8fafc',
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'transform 0.1s ease',
                    boxShadow: `0 0 10px ${
                      obj.type === 'job' ? 'rgba(16, 185, 129, 0.3)' :
                      obj.type === 'lead' ? 'rgba(59, 130, 246, 0.3)' :
                      obj.type === 'recruiter' ? 'rgba(139, 92, 246, 0.3)' : 'rgba(239, 68, 68, 0.3)'
                    }`,
                    animation: 'pulse-glow 2s infinite',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                >
                  {obj.label}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Legend */}
        {hasStarted && isWakingUp && (
          <div style={{
            display: 'flex', justifyContent: 'center', gap: 16,
            background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '8px 16px', fontSize: 11.5
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} /> Job (+100)</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }} /> Lead (+50)</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#8b5cf6' }} /> Recruiter (+250)</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} /> Spam (-100)</span>
          </div>
        )}
      </div>
    </div>
  );
};
