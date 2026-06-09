"use client";

import React, { useRef, useState, useEffect } from "react";
import { Playfair_Display, Inter } from "next/font/google";
import Link from "next/link";
import { motion, useInView } from "motion/react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Sphere, MeshDistortMaterial } from "@react-three/drei";
import { ArrowDown } from "lucide-react";
import * as THREE from "three";

const playfair = Playfair_Display({ 
  subsets: ["latin"], 
  weight: ["400", "600", "700"], 
  style: ["normal", "italic"] 
});

const inter = Inter({ 
  subsets: ["latin"], 
  weight: ["300", "400", "500", "600"] 
});

const AnimatedSphere = () => {
  const meshRef = useRef<THREE.Mesh>(null!);
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.getElapsedTime() * 0.1;
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.15;
    }
  });

  return (
    <Sphere ref={meshRef} args={[1, 64, 64]} scale={2.2}>
      <MeshDistortMaterial
        color="#C5A059"
        attach="material"
        distort={0.4}
        speed={1.5}
        roughness={0.7}
        metalness={0.5}
        wireframe={true}
        transparent
        opacity={0.3}
      />
    </Sphere>
  );
};

const NodeGrid = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.05 },
    },
  };

  const item = {
    hidden: { opacity: 0, scale: 0.5 },
    show: { opacity: 1, scale: 1 },
  };

  return (
    <motion.div
      ref={ref}
      variants={container}
      initial="hidden"
      animate={isInView ? "show" : "hidden"}
      className="grid grid-cols-5 gap-4 aspect-square w-full max-w-[400px] mx-auto p-4 border border-[#C5A059]/30 rounded-2xl bg-white/50 backdrop-blur-sm shadow-sm"
    >
      {Array.from({ length: 25 }).map((_, i) => (
        <motion.div
          key={i}
          variants={item}
          className={`w-full aspect-square rounded-full flex items-center justify-center ${
            [7, 12, 13, 17, 21].includes(i) 
              ? "bg-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.5)]" 
              : "bg-zinc-200"
          }`}
        >
            {[7, 12, 13, 17, 21].includes(i) && (
              <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
            )}
        </motion.div>
      ))}
    </motion.div>
  );
};

const NeuralTelemetry = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  
  return (
    <div ref={ref} className="flex flex-col items-center justify-center p-8 md:p-16 bg-[#1a1a1a] border border-zinc-800 rounded-3xl w-full max-w-3xl mx-auto shadow-2xl relative overflow-hidden">
        <div className="flex flex-col gap-8 w-full max-w-[400px]">
          {[...Array(4)].map((_, idx) => (
             <motion.div
               key={idx}
               initial={{ y: -20, opacity: 0 }}
               animate={isInView ? { y: 0, opacity: 1 } : {}}
               transition={{ delay: idx * 0.4, duration: 0.6 }}
               className="h-px bg-gradient-to-r from-transparent via-[#C5A059]/40 to-transparent w-full relative"
             >
                <motion.div 
                   animate={{ x: [0, 400], opacity: [0, 1, 0] }}
                   transition={{ repeat: Infinity, duration: 1.5, delay: idx * 0.3 }}
                   className="absolute top-1/2 -translate-y-1/2 -ml-2 w-4 h-4 rounded-full bg-[#C5A059] blur-[2px]"
                />
             </motion.div>
          ))}
          
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ delay: 1.8, duration: 0.5 }}
            className="mt-6 text-center"
          >
            <div className="inline-block px-6 py-2 border border-red-500/50 bg-red-500/10 text-red-500 rounded-full text-sm font-bold tracking-[0.2em] shadow-[0_0_20px_rgba(239,68,68,0.15)]">
               ANOMALY DETECTED
            </div>
          </motion.div>
        </div>
    </div>
  )
}

const ImpactChart = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  const bars = [
    { height: "80%", label: "2023", color: "bg-zinc-200" },
    { height: "85%", label: "2024", color: "bg-zinc-200" },
    { height: "51%", label: "2025", color: "bg-[#C5A059]", subtitle: "post-WaziGov" },
  ];

  return (
    <div ref={ref} className="flex items-end justify-center gap-6 sm:gap-12 h-[350px] mt-16 border-b border-zinc-200 pb-4 px-4">
      {bars.map((bar, i) => (
        <div key={i} className="flex flex-col items-center gap-4 w-16 sm:w-24">
          <div className="h-[250px] w-full flex items-end bg-zinc-100/50 rounded-t-xl overflow-hidden relative">
            <motion.div
              initial={{ height: "0%" }}
              animate={isInView ? { height: bar.height } : {}}
              transition={{ duration: 1.2, delay: i * 0.2 + 0.2, ease: [0.16, 1, 0.3, 1] }}
              className={`w-full ${bar.color}`}
            />
          </div>
          <div className="text-center">
             <span className="block text-xs font-bold text-zinc-600 tracking-wider uppercase">{bar.label}</span>
             {bar.subtitle && <span className="block text-[10px] uppercase tracking-wider text-[#C5A059] mt-1">{bar.subtitle}</span>}
          </div>
        </div>
      ))}
    </div>
  );
};

export default function WaziGovEditorial() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className={`min-h-screen bg-[#F9F8F4] text-[#1a1a1a] ${inter.className}`}>
      {/* Header/Nav */}
      <header 
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? "bg-[#F9F8F4]/80 backdrop-blur-md border-b border-zinc-200/50 py-4" : "bg-transparent py-6"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <div className="w-10 h-10 rounded bg-[#1a1a1a] flex items-center justify-center">
              <span className={`text-[#C5A059] font-bold text-lg ${playfair.className}`}>W</span>
            </div>
            <span className="font-bold text-xl tracking-tight hidden sm:block">WaziGov</span>
          </div>
          
          <nav className="hidden lg:flex items-center justify-end gap-8 text-sm font-medium tracking-wide flex-1">
            <a href="#intro" className="text-zinc-600 hover:text-[#C5A059] transition-colors">Introduction</a>
            <a href="#transparency" className="text-zinc-600 hover:text-[#C5A059] transition-colors">Intelligence</a>
            <a href="#impact" className="text-zinc-600 hover:text-[#C5A059] transition-colors">Overview</a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative h-screen flex flex-col items-center justify-center overflow-hidden pt-20">
        <div className="absolute inset-0 z-0 opacity-80 mix-blend-multiply">
          <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} color="#C5A059" />
            <AnimatedSphere />
          </Canvas>
          <div className="absolute inset-0 bg-gradient-to-b from-[#F9F8F4]/10 via-[#F9F8F4]/50 to-[#F9F8F4]"></div>
        </div>

        <div className="relative z-10 text-center max-w-4xl mx-auto px-6">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className={`text-6xl sm:text-7xl md:text-8xl lg:text-9xl tracking-tight text-[#1a1a1a] ${playfair.className}`}
          >
            WaziGov
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            className={`text-2xl md:text-4xl text-[#C5A059] italic mt-4 sm:mt-6 ${playfair.className}`}
          >
            Civic Data Intelligence
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
            className="mt-8 text-base md:text-lg text-zinc-600 max-w-2xl mx-auto leading-relaxed"
          >
            Real-time county budget telemetry cross-referenced with OAG findings and CoB expenditure signals for automated audit forensics.
          </motion.p>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
            className="mt-10 flex justify-center"
          >
            <Link href="/dashboard" className="bg-[#1a1a1a] text-[#F9F8F4] px-8 py-3 rounded-full text-sm sm:text-base font-medium hover:bg-[#C5A059] transition-colors duration-300 whitespace-nowrap shadow-lg">
              Enter Dashboard
            </Link>
          </motion.div>
        </div>

        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute bottom-12 left-1/2 -translate-x-1/2"
        >
          <a href="#intro" className="flex flex-col items-center gap-3 text-zinc-400 hover:text-[#C5A059] transition-colors">
            <span className="text-[10px] sm:text-xs font-semibold tracking-widest uppercase">Discover</span>
            <motion.div animate={{ y: [0, 8, 0] }} transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}>
               <ArrowDown className="w-4 h-4 sm:w-5 sm:h-5" />
            </motion.div>
          </a>
        </motion.div>
      </section>

      {/* Introduction (The Opacity Barrier) */}
      <section id="intro" className="py-24 md:py-32 px-6">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-24">
          <div className="lg:col-span-5 flex flex-col gap-6">
             <div className="w-12 h-1 bg-[#C5A059] rounded-full"></div>
             <h2 className={`text-4xl md:text-5xl leading-tight text-[#1a1a1a] ${playfair.className}`}>
               The Accountability<br/>Gap.
             </h2>
          </div>
          <div className="lg:col-span-7 prose prose-lg prose-zinc font-light leading-loose text-zinc-700">
             <p className="first-letter:text-7xl first-letter:font-bold first-letter:text-[#C5A059] first-letter:mr-3 first-letter:float-left first-letter:leading-none">
               Traditionally, tracking civic funds across decentralized county procurement ledgers has been an exercise in disconnected data analysis. Siloed audits and delayed forensic reports allow structural inefficiencies to remain hidden beneath standard accounting practices.
             </p>
             <p className="mt-6">
               WaziGov dismantles this barrier by introducing a unified civic data explorer that automatically aggregates, maps, and spots statistical anomalies between executed projects, CoB expenditure signals, and OAG audit findings.
             </p>
          </div>
        </div>
      </section>

      {/* The Transparency Code */}
      <section id="transparency" className="py-24 md:py-32 px-6 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16 md:mb-24">
            <h2 className={`text-4xl md:text-5xl lg:text-6xl text-[#1a1a1a] mb-6 ${playfair.className}`}>
              The Intelligence Engine
            </h2>
            <p className="text-lg text-zinc-600 max-w-2xl mx-auto">
              Mapping fragmented public ledgers into unified records to pass through cross-referenced regulatory checkpoints.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="order-2 lg:order-1">
              <NodeGrid />
            </div>
            <div className="order-1 lg:order-2 flex flex-col gap-8">
              <div>
                <h3 className="text-[#C5A059] font-bold text-sm tracking-widest uppercase mb-3">01. Data Aggregation</h3>
                <p className="text-zinc-700 leading-relaxed font-light">
                  Project telemetry, financial ledgers, and implementation statuses from various counties are centralized into a unified civic data explorer.
                </p>
              </div>
              <div>
                <h3 className="text-[#C5A059] font-bold text-sm tracking-widest uppercase mb-3">02. Triangulation Verdict</h3>
                <p className="text-zinc-700 leading-relaxed font-light">
                  Data points are cross-referenced against OAG audit forensics and CoB expenditure signals to automatically identify and flag high-risk projects.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Neural Telemetry (Dark Section) */}
      <section className="py-24 md:py-32 px-6 bg-[#0f0f0f] text-[#F9F8F4]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
             <div className="lg:col-span-5 flex flex-col gap-6">
                <div className="w-12 h-1 bg-[#C5A059] rounded-full"></div>
                <h2 className={`text-4xl md:text-5xl leading-tight ${playfair.className}`}>
                  Audit<br/>Forensics.
                </h2>
                <p className="text-zinc-400 font-light leading-relaxed mt-4">
                  A comprehensive risk assessment mechanism analyzes historical discrepancy patterns, mathematically isolating high-risk procurement clusters down to the specific administrative unit and project level.
                </p>
             </div>
             <div className="lg:col-span-7">
                <NeuralTelemetry />
             </div>
          </div>
        </div>
      </section>

      {/* Impact */}
      <section id="impact" className="py-24 md:py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className={`text-4xl md:text-5xl text-[#1a1a1a] mb-6 ${playfair.className}`}>
              National Overview
            </h2>
            <p className="text-xl text-zinc-600 max-w-2xl mx-auto font-light">
              Tracking implementation progress and budget utilization across <b className="text-[#C5A059] font-semibold">all 47 counties</b> to ensure value for public money.
            </p>
          </div>
          
          <ImpactChart />
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-12 px-6 border-t border-zinc-200">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <span className={`text-[#1a1a1a] font-bold text-xl ${playfair.className}`}>WaziGov</span>
          </div>
          <p className="text-xs text-zinc-400">© 2026 WaziGov Civic Project. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
