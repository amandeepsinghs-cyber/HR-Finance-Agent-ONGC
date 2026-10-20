'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Mic, MicOff, Send, BarChart3, PieChart, Activity, Clock, ShieldCheck, Sparkles } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'agent' | 'tool';
  text: string;
  timestamp: string;
  metadata?: any;
}

interface LatencyMetrics {
  toolStartMs: number | null;
  chartReadyMs: number | null;
  ttfbAudioMs: number | null;
  turnTotalMs: number | null;
  toolDurationMs: number | null;
}

export default function VoiceChartSpikePage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      role: 'agent',
      text: 'Namaste! I am the ONGC HR & Finance executive voice assistant. Speak or type your query regarding executive tenure, transfers, or policy rotation.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [toolStatus, setToolStatus] = useState<string>('Idle');
  const [language, setLanguage] = useState<'en-IN' | 'hi-IN'>('en-IN');
  const [activeChartView, setActiveChartView] = useState<'donut' | 'stacked_bar'>('donut');
  const [chartSpecData, setChartSpecData] = useState<any>(null);
  const [metrics, setMetrics] = useState<LatencyMetrics>({
    toolStartMs: null,
    chartReadyMs: null,
    ttfbAudioMs: null,
    turnTotalMs: null,
    toolDurationMs: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);
  const echartsInstanceRef = useRef<echarts.ECharts | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const turnStartTimeRef = useRef<number | null>(null);

  // Initialize ECharts instance
  useEffect(() => {
    if (chartRef.current && !echartsInstanceRef.current) {
      const myChart = echarts.init(chartRef.current, 'dark', {
        renderer: 'canvas',
      });
      echartsInstanceRef.current = myChart;

      const handleResize = () => myChart.resize();
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
        myChart.dispose();
      };
    }
  }, []);

  // Connect WebSocket to FastAPI backend
  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8100/ws/live?model=gemini-3.8-live&voice=Aoede&language=${language}`;
    console.log('[WS] Connecting to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected to Live Session');
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setIsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      const tNow = performance.now();

      switch (msg.type) {
        case 'connection_status':
          console.log('[WS] Ready:', msg);
          break;

        case 'user_transcript':
          setMessages((prev) => [
            ...prev,
            {
              id: `user-${Date.now()}`,
              role: 'user',
              text: msg.text,
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          break;

        case 'tool_call_start':
          setActiveTool(msg.tool);
          setToolStatus(`Executing ${msg.tool}...`);
          if (turnStartTimeRef.current) {
            const startMs = Math.round(tNow - turnStartTimeRef.current);
            setMetrics((m) => ({ ...m, toolStartMs: startMs }));
          }
          break;

        case 'tool_call_done':
          setActiveTool(null);
          setToolStatus(`Completed in ${msg.latency_ms}ms`);
          setMetrics((m) => ({ ...m, toolDurationMs: msg.latency_ms }));
          break;

        case 'chart_spec':
          console.log('[WS] Chart Spec received:', msg.spec);
          setChartSpecData(msg.spec);
          if (turnStartTimeRef.current) {
            const chartMs = Math.round(tNow - turnStartTimeRef.current);
            setMetrics((m) => ({ ...m, chartReadyMs: chartMs }));
          }
          renderChart(msg.spec, activeChartView);
          break;

        case 'agent_transcript':
          setMessages((prev) => [
            ...prev,
            {
              id: `agent-${Date.now()}`,
              role: 'agent',
              text: msg.text,
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          break;

        case 'audio':
          if (turnStartTimeRef.current && metrics.ttfbAudioMs === null) {
            const audioMs = Math.round(tNow - turnStartTimeRef.current);
            setMetrics((m) => ({ ...m, ttfbAudioMs: audioMs }));
          }
          playIncomingAudio(msg.data);
          break;

        case 'turn_complete':
          if (turnStartTimeRef.current) {
            const totalMs = Math.round(tNow - turnStartTimeRef.current);
            setMetrics((m) => ({
              ...m,
              turnTotalMs: totalMs,
              ttfbAudioMs: m.ttfbAudioMs || msg.metrics?.ttfb_audio_ms || null,
              toolStartMs: m.toolStartMs || msg.metrics?.tool_start_ms || null,
              chartReadyMs: m.chartReadyMs || msg.metrics?.chart_ready_ms || null,
              toolDurationMs: m.toolDurationMs || msg.metrics?.tool_duration_ms || null,
            }));
          }
          turnStartTimeRef.current = null;
          break;

        default:
          break;
      }
    };

    return () => {
      ws.close();
    };
  }, [language]);

  // Render ECharts spec based on view (donut vs stacked bar)
  const renderChart = (spec: any, view: 'donut' | 'stacked_bar') => {
    if (!echartsInstanceRef.current || !spec) return;

    const baseOptions: any = {
      backgroundColor: 'transparent',
      title: spec.title || { text: 'Headcount Analysis' },
      tooltip: spec.tooltip || { trigger: 'item' },
      legend: spec.legend || { orient: 'horizontal', bottom: 0 },
      color: spec.color || [
        '#1E3A8A', '#2563EB', '#3B82F6', '#0D9488', '#10B981',
        '#F59E0B', '#EA580C', '#DC2626', '#8B5CF6'
      ],
      animation: true,
      animationDuration: 900,
      animationEasing: 'cubicOut',
    };

    if (view === 'donut' && spec.views?.donut) {
      baseOptions.series = spec.views.donut.series;
      delete baseOptions.xAxis;
      delete baseOptions.yAxis;
      delete baseOptions.grid;
    } else if (view === 'stacked_bar' && spec.views?.stacked_bar) {
      baseOptions.xAxis = spec.views.stacked_bar.xAxis;
      baseOptions.yAxis = spec.views.stacked_bar.yAxis;
      baseOptions.series = spec.views.stacked_bar.series;
      baseOptions.grid = spec.grid || { top: '15%', left: '8%', right: '8%', bottom: '20%', containLabel: true };
    } else if (spec.series) {
      baseOptions.series = spec.series;
    }

    echartsInstanceRef.current.setOption(baseOptions, true);
  };

  // Switch view tabs
  const handleSwitchView = (view: 'donut' | 'stacked_bar') => {
    setActiveChartView(view);
    if (chartSpecData) {
      renderChart(chartSpecData, view);
    }
  };

  // Audio playback for incoming 24kHz PCM chunks
  const playIncomingAudio = async (base64Data: string) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 24000,
        });
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }

      const binaryStr = atob(base64Data);
      const len = binaryStr.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      const buffer = ctx.createBuffer(1, float32Array.length, 24000);
      buffer.copyToChannel(float32Array, 0);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      source.start();
    } catch (e) {
      console.warn('[Audio Playback] Error playing audio:', e);
    }
  };

  // Send text query
  const handleSendText = (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || !wsRef.current) return;

    turnStartTimeRef.current = performance.now();
    setMetrics({
      toolStartMs: null,
      chartReadyMs: null,
      ttfbAudioMs: null,
      turnTotalMs: null,
      toolDurationMs: null,
    });

    wsRef.current.send(
      JSON.stringify({
        type: 'query_simulate',
        text: text.trim(),
        language: language,
      })
    );

    setInputText('');
  };

  // Toggle Microphone Audio Recording (AudioWorklet 16kHz PCM)
  const toggleRecording = async () => {
    if (isRecording) {
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
      }
      setIsRecording(false);
      // Mark end of user speech
      turnStartTimeRef.current = performance.now();
      if (wsRef.current) {
        wsRef.current.send(JSON.stringify({ type: 'audio_stream_end' }));
      }
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });
        micStreamRef.current = stream;

        const audioCtx = new AudioContext({ sampleRate: 16000 });
        await audioCtx.audioWorklet.addModule('/worklets/pcm-recorder-processor.js');

        const micSource = audioCtx.createMediaStreamSource(stream);
        const workletNode = new AudioWorkletNode(audioCtx, 'pcm-recorder-processor');

        workletNode.port.onmessage = (e) => {
          const pcmBuffer = e.data as ArrayBuffer;
          const pcmBytes = new Uint8Array(pcmBuffer);
          let binary = '';
          for (let i = 0; i < pcmBytes.byteLength; i++) {
            binary += String.fromCharCode(pcmBytes[i]);
          }
          const base64Data = btoa(binary);

          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                type: 'audio',
                data: base64Data,
              })
            );
          }
        };

        micSource.connect(workletNode);
        setIsRecording(true);
      } catch (err) {
        console.warn('Microphone permission not granted or unsupported:', err);
        alert('Microphone input simulated via quick prompt chips.');
      }
    }
  };

  return (
    <div className="spike-app">
      {/* Header */}
      <header className="spike-header">
        <div className="logo-area">
          <div className="ongc-badge">ONGC</div>
          <div className="app-title">
            <h1>HR & Finance Voice-to-Chart Spike</h1>
            <p>Gemini Live Native Audio (ADK bidi-streaming) • ECharts Interactive Visualisation</p>
          </div>
        </div>

        <div className="header-status">
          <span className="badge badge-green" style={{ border: '1px solid #10b981', background: 'rgba(16, 185, 129, 0.15)', fontWeight: 'bold' }}>
            ● LIVE (Vertex AI us-central1 + BigQuery)
          </span>
          <span className={`badge ${isConnected ? 'badge-green' : 'badge-amber'}`}>
            ● {isConnected ? 'WebSocket Connected' : 'Connecting...'}
          </span>
          <span className="badge badge-blue">Model: gemini-3.8-live</span>
          <span className="badge badge-amber">Voice: Aoede (Female)</span>
          <button
            className="prompt-chip"
            onClick={() => setLanguage(language === 'en-IN' ? 'hi-IN' : 'en-IN')}
          >
            Lang: {language}
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="main-content">
        {/* Left Column: Transcript & Controls */}
        <section className="panel">
          <div className="panel-header">
            <h2>Transcript Thread & Voice Stream</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
              <ShieldCheck size={14} color="#34d399" />
              <span>LIVE GROUNDING: BigQuery hrfin_gold & JRTP Search</span>
            </div>
          </div>

          <div className="transcript-thread">
            {messages.map((m) => (
              <div key={m.id} className={`message-bubble ${m.role}`}>
                <div>{m.text}</div>
                <div className="message-meta">{m.timestamp}</div>
              </div>
            ))}
          </div>

          {/* Active Tool Status */}
          <div className="tool-status-callout">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={16} className={activeTool ? 'tool-active' : ''} />
              <span>Status: {toolStatus}</span>
            </div>
            {metrics.toolDurationMs !== null && (
              <span style={{ fontFamily: 'var(--font-mono)' }}>
                Tool Latency: {metrics.toolDurationMs}ms
              </span>
            )}
          </div>

          {/* Input & Mic Controls */}
          <div className="controls-area">
            <div className="quick-prompts">
              <button
                className="prompt-chip"
                onClick={() =>
                  handleSendText(
                    'How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.'
                  )
                }
              >
                📊 English: Delhi ≥5yr
              </button>
              <button
                className="prompt-chip"
                onClick={() =>
                  handleSendText('Delhi mein 5 saal se zyada kitne executives hain, grade-wise batao')
                }
              >
                🇮🇳 Hinglish: Delhi 5 saal+
              </button>
              <button className="prompt-chip" onClick={() => handleSendText('only E5 and above')}>
                🔍 Follow-up: E5+ only
              </button>
              <button
                className="prompt-chip"
                onClick={() => handleSendText('how long must I stay at a station before transfer?')}
              >
                📜 Policy: Station tenure
              </button>
            </div>

            <div className="input-row">
              <button
                className={`btn btn-mic ${isRecording ? 'recording' : ''}`}
                onClick={toggleRecording}
                title="Toggle Mic Recording"
              >
                {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                {isRecording ? 'Listening...' : 'Mic'}
              </button>

              <input
                type="text"
                className="text-input"
                placeholder="Ask about Delhi executives tenure or transfer policy..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendText()}
              />

              <button className="btn btn-primary" onClick={() => handleSendText()}>
                <Send size={18} />
              </button>
            </div>
          </div>
        </section>

        {/* Right Column: ECharts Canvas */}
        <section className="panel">
          <div className="panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <BarChart3 size={18} color="#38bdf8" />
              <h2>Interactive Visualization Canvas</h2>
            </div>

            <div className="chart-toolbar">
              <button
                className={`btn-tab ${activeChartView === 'donut' ? 'active' : ''}`}
                onClick={() => handleSwitchView('donut')}
              >
                <PieChart size={14} style={{ display: 'inline', marginRight: 4 }} />
                Donut (Grade)
              </button>
              <button
                className={`btn-tab ${activeChartView === 'stacked_bar' ? 'active' : ''}`}
                onClick={() => handleSwitchView('stacked_bar')}
              >
                <BarChart3 size={14} style={{ display: 'inline', marginRight: 4 }} />
                Stacked Bar (Discipline)
              </button>
            </div>
          </div>

          <div className="chart-container-box">
            <div ref={chartRef} className="echarts-canvas-div" />
          </div>
        </section>
      </main>

      {/* Latency HUD */}
      <footer className="latency-hud">
        <div className="hud-metric">
          <div className="hud-label">Time to Tool Start</div>
          <div className="hud-value">
            {metrics.toolStartMs !== null ? `${metrics.toolStartMs} ms` : '—'}
          </div>
        </div>

        <div className="hud-metric">
          <div className="hud-label">Time to Chart Rendered</div>
          <div className="hud-value">
            {metrics.chartReadyMs !== null ? `${metrics.chartReadyMs} ms` : '—'}
          </div>
        </div>

        <div className="hud-metric">
          <div className="hud-label">TTFB Audio (1st Byte)</div>
          <div className="hud-value">
            {metrics.ttfbAudioMs !== null ? `${metrics.ttfbAudioMs} ms` : '—'}
          </div>
        </div>

        <div className="hud-metric">
          <div className="hud-label">Total Turn Duration</div>
          <div className="hud-value">
            {metrics.turnTotalMs !== null ? `${metrics.turnTotalMs} ms` : '—'}
          </div>
        </div>
      </footer>
    </div>
  );
}
