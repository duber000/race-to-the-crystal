/**
 * AudioManager - Web Audio API Module
 * Handles background music, generator hums, and sound effects
 * 
 * Supports both synthesized sounds (Web Audio API) and pre-recorded audio files
 */

class AudioManager {
    constructor() {
        this.audioContext = null;
        this.soundsEnabled = true;
        this.musicEnabled = true;

        // Background music
        this.backgroundMusic = null;
        this.musicVolume = 0.3;
        this.musicPlaying = false;

        // Generator hums (4 separate tracks)
        this.generatorHums = [];
        this.generatorHumSources = [];
        this.generatorHumGains = [];
        this.generatorHumEnabled = false;
        this.humVolume = 0.2;

        // Crystal hum
        this.crystalHum = null;
        this.crystalHumEnabled = false;

        // Sound effects cache
        this.soundEffects = new Map();
        this.activeSoundPlayers = [];

        // Audio file paths
        this.musicPath = '/static/assets/music/techno.mp3';
        this.generatorHumPaths = [
            '/static/assets/music/generator_0_hum.wav',
            '/static/assets/music/generator_1_hum.wav',
            '/static/assets/music/generator_2_hum.wav',
            '/static/assets/music/generator_3_hum.wav',
        ];
        this.soundEffectPaths = {
            move: '/static/assets/sounds/sliding.wav',
            deploy: '/static/assets/sounds/sliding.wav',
            attack: '/static/assets/sounds/flushing.wav',
            mystery: '/static/assets/sounds/mystery_bing.wav',
            generator_explosion: '/static/assets/sounds/generator_explosion.wav',
            crystal_shatter: '/static/assets/sounds/crystal_shatter.wav',
        };
    }

    /**
     * Initialize audio context (must be called after user interaction)
     */
    initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }

        return this.audioContext;
    }

    /**
     * Load background music
     */
    async loadBackgroundMusic() {
        if (!this.musicEnabled) return;

        try {
            const response = await fetch(this.musicPath);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.decodeAudio(arrayBuffer);

            this.backgroundMusic = audioBuffer;
            console.log('[AudioManager] Background music loaded');

            // Start playing if music is enabled
            if (this.musicPlaying) {
                this.playBackgroundMusic();
            }
        } catch (error) {
            console.error('[AudioManager] Failed to load background music:', error);
        }
    }

    /**
     * Load generator hum tracks
     */
    async loadGeneratorHums() {
        for (let i = 0; i < this.generatorHumPaths.length; i++) {
            try {
                const response = await fetch(this.generatorHumPaths[i]);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const arrayBuffer = await response.arrayBuffer();
                const audioBuffer = await this.decodeAudio(arrayBuffer);

                this.generatorHums[i] = audioBuffer;
                console.log(`[AudioManager] Generator ${i} hum loaded`);
            } catch (error) {
                console.error(`[AudioManager] Failed to load generator ${i} hum:`, error);
                this.generatorHums[i] = null;
            }
        }

        // Enable generator hums after loading
        this.generatorHumEnabled = true;
        this.updateGeneratorHums([]);
    }

    /**
     * Load all sound effects
     */
    async loadSoundEffects() {
        const loadPromises = [];

        for (const [name, path] of Object.entries(this.soundEffectPaths)) {
            const promise = this.loadSoundEffect(name, path);
            loadPromises.push(promise);
        }

        await Promise.all(loadPromises);
        console.log('[AudioManager] All sound effects loaded');
    }

    /**
     * Load a single sound effect
     */
    async loadSoundEffect(name, path) {
        try {
            const response = await fetch(path);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.decodeAudio(arrayBuffer);

            this.soundEffects.set(name, audioBuffer);
            console.log(`[AudioManager] Sound effect loaded: ${name}`);
        } catch (error) {
            console.error(`[AudioManager] Failed to load sound effect ${name}:`, error);
            this.soundEffects.set(name, null);
        }
    }

    /**
     * Decode audio data
     */
    async decodeAudio(arrayBuffer) {
        if (!this.audioContext) {
            this.initAudioContext();
        }

        try {
            return await this.audioContext.decodeAudioData(arrayBuffer);
        } catch (error) {
            console.error('[AudioManager] Failed to decode audio:', error);
            throw error;
        }
    }

    /**
     * Play background music in a loop
     */
    playBackgroundMusic() {
        if (!this.backgroundMusic || !this.musicEnabled) return;

        this.stopBackgroundMusic();

        const source = this.audioContext.createBufferSource();
        source.buffer = this.backgroundMusic;
        source.loop = true;

        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = this.musicVolume;

        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        source.start(0);

        this.backgroundMusicSource = source;
        this.backgroundMusicGain = gainNode;
        this.musicPlaying = true;

        console.log('[AudioManager] Background music playing');
    }

    /**
     * Stop background music
     */
    stopBackgroundMusic() {
        if (this.backgroundMusicSource) {
            try {
                this.backgroundMusicSource.stop();
            } catch (e) {
                // Already stopped
            }
            this.backgroundMusicSource = null;
        }
        this.backgroundMusicGain = null;
        this.musicPlaying = false;
    }

    /**
     * Toggle music on/off
     */
    toggleMusic() {
        this.initAudioContext();

        if (this.musicPlaying) {
            this.stopBackgroundMusic();
            this.stopGeneratorHums();
            console.log('[AudioManager] Music paused');
        } else {
            this.musicEnabled = true;
            this.playBackgroundMusic();
            this.updateGeneratorHums([]);
            console.log('[AudioManager] Music resumed');
        }
    }

    /**
     * Update generator hums based on game state
     */
    updateGeneratorHums(generators) {
        if (!this.generatorHumEnabled || !this.musicEnabled) return;

        // Stop all hums first
        this.stopGeneratorHums();

        // Start hums for active generators
        for (let i = 0; i < generators.length; i++) {
            const generator = generators[i];

            if (!generator.is_disabled && this.generatorHums[i]) {
                this.startGeneratorHum(i);
            }
        }
    }

    /**
     * Start a specific generator hum
     */
    startGeneratorHum(generatorIndex) {
        if (!this.generatorHums[generatorIndex]) return;

        const source = this.audioContext.createBufferSource();
        source.buffer = this.generatorHums[generatorIndex];
        source.loop = true;

        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = this.humVolume;

        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        source.start(0);

        this.generatorHumSources[generatorIndex] = source;
        this.generatorHumGains[generatorIndex] = gainNode;

        console.log(`[AudioManager] Generator ${generatorIndex} hum started`);
    }

    /**
     * Stop all generator hums
     */
    stopGeneratorHums() {
        this.generatorHumSources = [];
        this.generatorHumGains = [];
    }

    /**
     * Play a sound effect
     */
    playSound(soundName) {
        if (!this.soundsEnabled) return;

        this.initAudioContext();

        const soundBuffer = this.soundEffects.get(soundName);
        if (!soundBuffer) {
            console.warn(`[AudioManager] Sound effect not found: ${soundName}`);
            return;
        }

        const source = this.audioContext.createBufferSource();
        source.buffer = soundBuffer;

        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = 0.5;

        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        source.start(0);

        // Keep reference for cleanup
        this.activeSoundPlayers.push({ source, gainNode });

        // Clean up old players
        if (this.activeSoundPlayers.length > 20) {
            this.activeSoundPlayers.shift();
        }

        console.log(`[AudioManager] Playing sound: ${soundName}`);
    }

    /**
     * Enable or disable all sounds
     */
    setSoundsEnabled(enabled) {
        this.soundsEnabled = enabled;

        if (!enabled) {
            this.stopAllSounds();
        }
    }

    /**
     * Stop all sounds
     */
    stopAllSounds() {
        this.stopBackgroundMusic();
        this.stopGeneratorHums();

        for (const player of this.activeSoundPlayers) {
            try {
                player.source.stop();
            } catch (e) {
                // Already stopped
            }
        }
        this.activeSoundPlayers = [];
    }

    /**
     * Set music volume (0.0 to 1.0)
     */
    setMusicVolume(volume) {
        this.musicVolume = Math.max(0, Math.min(1, volume));

        if (this.backgroundMusicGain) {
            this.backgroundMusicGain.gain.value = this.musicVolume;
        }
    }

    /**
     * Set hum volume (0.0 to 1.0)
     */
    setHumVolume(volume) {
        this.humVolume = Math.max(0, Math.min(1, volume));

        for (const gainNode of this.generatorHumGains) {
            if (gainNode) {
                gainNode.gain.value = this.humVolume;
            }
        }
    }

    /**
     * Play synthesized sound (fallback when audio files not available)
     */
    playSynthesizedSound(soundName) {
        if (!this.soundsEnabled) return;

        this.initAudioContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        switch (soundName) {
            case 'move':
            case 'deploy':
                this._playSlidingSound(ctx, now);
                break;
            case 'attack':
                this._playFlushingSound(ctx, now);
                break;
            case 'capture':
                this._playGeneratorExplosionSound(ctx, now);
                break;
            case 'crystal':
                this._playCrystalShatterSound(ctx, now);
                break;
            case 'mystery':
                this._playMysteryBingSound(ctx, now);
                break;
            case 'fog_horn':
                this._playFogHornSound(ctx, now);
                break;
            case 'ghost':
                this._playGhostSound(ctx, now);
                break;
            case 'lightning':
                this._playLightningSound(ctx, now);
                break;
            case 'whoosh':
                this._playWhooshSound(ctx, now);
                break;
            default:
                this._playDeploySound(ctx, now);
                break;
        }
    }

    _playSlidingSound(ctx, now) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(1000, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.5);

        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(2000, now);
        filter.frequency.exponentialRampToValueAtTime(500, now + 0.5);

        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.5);
    }

    _playFlushingSound(ctx, now) {
        const duration = 2.0;
        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * duration, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;

        const noiseFilter = ctx.createBiquadFilter();
        noiseFilter.type = 'bandpass';
        noiseFilter.frequency.setValueAtTime(800, now);
        noiseFilter.frequency.exponentialRampToValueAtTime(100, now + duration);
        noiseFilter.Q.value = 1;

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.setValueAtTime(0.2, now + duration * 0.7);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        noise.connect(noiseFilter);
        noiseFilter.connect(gain);
        gain.connect(ctx.destination);

        noise.start(now);
        noise.stop(now + duration);
    }

    _playGeneratorExplosionSound(ctx, now) {
        const duration = 1.2;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.exponentialRampToValueAtTime(30, now + duration);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.3, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.1));
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.4, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);
    }

    _playCrystalShatterSound(ctx, now) {
        const duration = 1.5;

        for (let i = 0; i < 10; i++) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            const freq = 2000 + Math.random() * 6000;
            const decay = 0.5 + Math.random() * 2.0;

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now);

            gain.gain.setValueAtTime(0.05, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + decay);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now);
            osc.stop(now + decay);
        }

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.1, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.2, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);
    }

    _playMysteryBingSound(ctx, now) {
        const duration = 0.3;
        const mainFreq = 1500;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(mainFreq, now);

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(0.3, now + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        [1.8, 2.5, 3.2].forEach((mult, idx) => {
            const harm = ctx.createOscillator();
            const harmGain = ctx.createGain();
            harm.type = 'sine';
            harm.frequency.setValueAtTime(mainFreq * mult, now);
            harmGain.gain.setValueAtTime((0.1 * (3 - idx)) / 3, now);
            harmGain.gain.exponentialRampToValueAtTime(0.001, now + duration);
            harm.connect(harmGain);
            harmGain.connect(ctx.destination);
            harm.start(now);
            harm.stop(now + duration);
        });
    }

    _playDeploySound(ctx, now) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(1200, now + 0.1);

        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.2);
    }

    _playFogHornSound(ctx, now) {
        const duration = 1.5;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(80, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + duration);

        lfo.type = 'sine';
        lfo.frequency.value = 5;
        lfoGain.gain.value = 3;
        lfo.connect(lfoGain);
        lfoGain.connect(osc.frequency);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.setValueAtTime(0.3, now + duration * 0.7);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        lfo.start(now);
        osc.stop(now + duration);
        lfo.stop(now + duration);
    }

    _playGhostSound(ctx, now) {
        const duration = 1.2;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(400, now);
        osc.frequency.setValueAtTime(600, now + duration * 0.3);
        osc.frequency.setValueAtTime(350, now + duration * 0.6);
        osc.frequency.setValueAtTime(500, now + duration);

        filter.type = 'lowpass';
        filter.frequency.value = 1000;
        filter.Q.value = 5;

        gain.gain.setValueAtTime(0.2, now);
        gain.gain.setValueAtTime(0.2, now + duration * 0.5);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + duration);

        for (let i = 0; i < 3; i++) {
            const harm = ctx.createOscillator();
            const harmGain = ctx.createGain();
            harm.type = 'sine';
            harm.frequency.setValueAtTime(800 + i * 200, now);
            harmGain.gain.setValueAtTime(0.05 * (3 - i) / 3, now);
            harmGain.gain.exponentialRampToValueAtTime(0.001, now + duration);
            harm.connect(harmGain);
            harmGain.connect(ctx.destination);
            harm.start(now);
            harm.stop(now + duration);
        }
    }

    _playLightningSound(ctx, now) {
        const duration = 0.5;

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.01));
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;
        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.5, now);
        noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);

        noise.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        noise.start(now);

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const filter = ctx.createBiquadFilter();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(100, now + 0.1);
        osc.frequency.exponentialRampToValueAtTime(40, now + duration);

        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(200, now);
        filter.Q.value = 2;

        gain.gain.setValueAtTime(0, now + 0.1);
        gain.gain.linearRampToValueAtTime(0.2, now + 0.15);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + 0.1);
        osc.stop(now + duration);
    }

    _playWhooshSound(ctx, now) {
        const duration = 1.0;

        const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * duration, ctx.sampleRate);
        const noiseData = noiseBuffer.getChannelData(0);
        for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = Math.random() * 2 - 1;
        }

        const noise = ctx.createBufferSource();
        noise.buffer = noiseBuffer;

        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(200, now);
        filter.frequency.exponentialRampToValueAtTime(2000, now + duration * 0.5);
        filter.frequency.exponentialRampToValueAtTime(500, now + duration);
        filter.Q.value = 2;

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.linearRampToValueAtTime(0.25, now + duration * 0.3);
        gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);

        noise.start(now);
        noise.stop(now + duration);
    }

    /**
     * Cleanup audio resources
     */
    cleanup() {
        this.stopAllSounds();

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        this.soundEffects.clear();
        this.generatorHums = [];
        this.backgroundMusic = null;
    }
}

// Export for module usage
export { AudioManager };
