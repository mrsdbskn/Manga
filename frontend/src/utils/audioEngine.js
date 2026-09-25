/**
 * utils/audioEngine.js - Web Audio API synthesized sound generator for manga reading.
 * Provides zero-asset, procedural page-turn sound effects and Grand Line ambient soundscapes
 * (ocean waves, deck rain, sail wind) with reactive volume and persistence.
 */

let audioCtx = null;
let ambientGainNode = null;
let ambientSource = null;
let currentAmbientMode = localStorage.getItem('op_ambient_mode') || 'off';
let isSfxEnabled = localStorage.getItem('op_sfx_enabled') !== 'false';
let ambientVolume = parseFloat(localStorage.getItem('op_ambient_volume') || '0.25');

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Procedural paper flutter/page-flip sound effect using filtered white noise and envelope decay.
 */
export function playPageFlipSound() {
  if (!isSfxEnabled) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const bufferSize = ctx.sampleRate * 0.12; // 120ms duration
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      // White noise with subtle granular variation
      data[i] = Math.random() * 2 - 1;
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    // Bandpass filter to mimic paper texture resonance
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1400 + Math.random() * 400, ctx.currentTime);
    filter.Q.setValueAtTime(1.2, ctx.currentTime);

    // Dynamic gain envelope
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.01, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.11);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noise.start();
    noise.stop(ctx.currentTime + 0.12);
  } catch (err) {
    console.debug('Page flip audio error:', err);
  }
}

/**
 * Procedural ambient sound generator for ocean waves, rain, and wind.
 */
export function setAmbientMode(mode) {
  currentAmbientMode = mode;
  localStorage.setItem('op_ambient_mode', mode);

  if (ambientSource) {
    try {
      ambientSource.stop();
      ambientSource.disconnect();
    } catch {}
    ambientSource = null;
  }

  if (mode === 'off') return;

  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    // 5-second looping brown/pink noise buffer
    const bufferSize = ctx.sampleRate * 5;
    const buffer = ctx.createBuffer(2, bufferSize, ctx.sampleRate);
    const left = buffer.getChannelData(0);
    const right = buffer.getChannelData(1);

    let lastLeft = 0;
    let lastRight = 0;

    for (let i = 0; i < bufferSize; i++) {
      const whiteLeft = Math.random() * 2 - 1;
      const whiteRight = Math.random() * 2 - 1;

      if (mode === 'ocean' || mode === 'wind') {
        // Brown noise (integrated white noise) for soft wave roar
        lastLeft = (lastLeft + 0.02 * whiteLeft) / 1.02;
        lastRight = (lastRight + 0.02 * whiteRight) / 1.02;
      } else {
        // Pink noise for rain
        lastLeft = (lastLeft * 0.9 + whiteLeft * 0.1);
        lastRight = (lastRight * 0.9 + whiteRight * 0.1);
      }
      left[i] = lastLeft * 3.5;
      right[i] = lastRight * 3.5;
    }

    ambientSource = ctx.createBufferSource();
    ambientSource.buffer = buffer;
    ambientSource.loop = true;

    const filter = ctx.createBiquadFilter();
    if (mode === 'ocean') {
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(450, ctx.currentTime);
      // Create subtle LFO for ocean wave swell
      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.frequency.setValueAtTime(0.12, ctx.currentTime); // Wave every ~8 seconds
      lfoGain.gain.setValueAtTime(280, ctx.currentTime);
      lfo.connect(filter.frequency);
      lfo.start();
    } else if (mode === 'rain') {
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(1100, ctx.currentTime);
      filter.Q.setValueAtTime(0.7, ctx.currentTime);
    } else if (mode === 'wind') {
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(320, ctx.currentTime);
    }

    ambientGainNode = ctx.createGain();
    ambientGainNode.gain.setValueAtTime(ambientVolume, ctx.currentTime);

    ambientSource.connect(filter);
    filter.connect(ambientGainNode);
    ambientGainNode.connect(ctx.destination);

    ambientSource.start();
  } catch (err) {
    console.debug('Ambient audio start error:', err);
  }
}

export function setAmbientVolume(vol) {
  ambientVolume = Math.max(0, Math.min(1, vol));
  localStorage.setItem('op_ambient_volume', String(ambientVolume));
  if (ambientGainNode && audioCtx) {
    ambientGainNode.gain.setValueAtTime(ambientVolume, audioCtx.currentTime);
  }
}

export function toggleSfx(enabled) {
  isSfxEnabled = enabled;
  localStorage.setItem('op_sfx_enabled', String(enabled));
  return isSfxEnabled;
}

export function getAudioSettings() {
  return {
    sfxEnabled: isSfxEnabled,
    ambientMode: currentAmbientMode,
    ambientVolume: ambientVolume,
  };
}
