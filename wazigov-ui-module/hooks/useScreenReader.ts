'use client';

import { useCallback, useState } from 'react';

export const useScreenReader = () => {
  // Keeps track of whether the robotic voice is currently talking
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = useCallback((text: string) => {
    // Check if the user's browser actually supports text-to-speech
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      console.warn('Speech synthesis not supported in this browser.');
      return;
    }

    // Stop any existing speech before starting a new one
    window.speechSynthesis.cancel();

    // Create the "utterance" (the packet of text to be spoken)
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Optional: Try to find a local accent (like Kenyan English or British English)
    const voices = window.speechSynthesis.getVoices();
    const localVoice = voices.find(v => v.lang.includes('en-KE') || v.lang.includes('en-GB'));
    if (localVoice) utterance.voice = localVoice;

    // Update state so our UI knows when to show the "Stop" button
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    // Speak!
    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return { speak, stop, isSpeaking };
};