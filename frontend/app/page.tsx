"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";

/**
 * Types based on the Scraper API
 */
interface SocialMediaData {
  platform: string;
  post_text: string;
  media_urls: string[];
  is_video: boolean;
}

interface ScrapedPage {
  metadata: {
    url: string;
    title: string;
    description: string;
  };
  headings: Record<string, string[]>;
  paragraphs: string[];
  links: string[];
  social_data?: SocialMediaData | null;
}

interface PipelineResponse {
  total_found: number;
  scraped_count: number;
  results: ScrapedPage[];
  storage_path: string;
}

export default function Dashboard() {
  const [query, setQuery] = useState("");
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScrapedPage[]>([]);
  const [status, setStatus] = useState<string>("Ready");
  const [error, setError] = useState<string | null>(null);
  const [storagePath, setStoragePath] = useState<string | null>(null);

  const startScrape = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setResults([]);
    setStatus("Initiating Pipeline...");

    try {
      const response = await fetch("http://localhost:8010/api/v1/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, pages }),
      });

      if (!response.ok) throw new Error("Search failed. Ensure backend is running.");

      const data: PipelineResponse = await response.json();
      setResults(data.results);
      setStoragePath(data.storage_path);
      setStatus(`Completed: ${data.scraped_count} pages scraped.`);
    } catch (err: any) {
      setError(err.message);
      setStatus("Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#0a0a0a] text-zinc-100 font-sans">
      {/* Header */}
      <header className="border-b border-white/10 glass-panel sticky top-0 z-50 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/20">
            <span className="font-bold text-xl">W</span>
          </div>
          <h1 className="text-xl font-semibold tracking-tight">W2B <span className="text-blue-500 font-light">Scraper</span></h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 bg-zinc-900 border border-white/5 rounded-full text-xs text-zinc-400">
            <span className={`w-2 h-2 rounded-full ${status === "Error" ? "bg-red-500" : "bg-green-500"}`}></span>
            API: {status}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full p-8 space-y-12">
        {/* Search Panel */}
        <section className="glass-panel rounded-3xl p-8 max-w-4xl mx-auto space-y-6 animate-fade-in">
          <div className="space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">Deep Web Intelligence</h2>
            <p className="text-zinc-400">Enter a query to discover and extract deep content from social media and across the web.</p>
          </div>
          
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative group">
              <input 
                type="text" 
                placeholder="Search phrase (e.g., python web scraping)..."
                className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 px-6 focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all text-lg"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-20 pointer-events-none">⌘ K</div>
            </div>
            
            <div className="w-full md:w-48 bg-black/40 border border-white/10 rounded-2xl py-4 px-6 flex flex-col justify-center">
              <label className="text-[10px] uppercase font-bold text-zinc-500 mb-1">Max Pages</label>
              <input 
                type="range" min="1" max="10" step="1"
                className="w-full accent-blue-500 cursor-pointer"
                value={pages}
                onChange={(e) => setPages(parseInt(e.target.value))}
              />
              <div className="text-xs text-center mt-1 font-mono text-blue-400">{pages} Pages</div>
            </div>
            
            <button 
              disabled={loading}
              onClick={startScrape}
              className={`px-8 py-4 rounded-2xl font-bold transition-all shadow-xl shadow-blue-600/20 active:scale-95 flex items-center justify-center gap-2
                ${loading ? "bg-zinc-800 text-zinc-500 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-500 text-white"}`}
            >
              {loading ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              ) : "🚀 Execute Pipeline"}
            </button>
          </div>
          
          {storagePath && (
            <div className="bg-blue-600/10 border border-blue-500/20 p-4 rounded-2xl flex items-center justify-between group">
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-bold text-blue-500">Local Data Storage</span>
                <div className="text-xs font-mono text-zinc-300 break-all">{storagePath}</div>
              </div>
              <div className="text-xl opacity-20 group-hover:opacity-100 transition-opacity">📁</div>
            </div>
          )}

          {error && <div className="text-red-400 text-sm bg-red-400/5 border border-red-400/10 p-3 rounded-xl text-center">{error}</div>}
        </section>

        {/* Results Section */}
        <section className="space-y-8">
          <div className="flex items-center justify-between border-b border-white/5 pb-4">
            <h3 className="text-xl font-medium tracking-tight flex items-center gap-3">
              Extraction Results
              <span className="bg-white/5 px-2 py-0.5 rounded-md text-xs font-mono text-zinc-500">{results.length} Pages</span>
            </h3>
            <button 
              disabled={results.length === 0}
              className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-30 disabled:pointer-events-none"
            >
              ↓ Export to Data (JSON)
            </button>
          </div>

          {!loading && results.length === 0 && !error && (
            <div className="flex flex-col items-center py-32 opacity-30 select-none">
              <div className="text-6xl mb-4">🔎</div>
              <p>No results yet. Start a search to see the magic happen.</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((result, idx) => (
              <ResultCard key={idx} result={result} />
            ))}
          </div>
        </section>
      </main>
      
      <footer className="border-t border-white/5 py-12 px-8 text-center text-zinc-600 text-xs mt-auto">
        &copy; 2026 W2B Scraper Dashboard. Deepmind Agentic Architecture.
      </footer>
    </div>
  );
}

function ResultCard({ result }: { result: ScrapedPage }) {
  const isSocial = !!result.social_data;
  const socialData = result.social_data;
  
  return (
    <article className="glass-panel rounded-2xl overflow-hidden flex flex-col group animate-fade-in hover:border-blue-500/30 transition-all">
      {/* Media Header (for Social) */}
      {isSocial && socialData && socialData.media_urls && socialData.media_urls.length > 0 && (
        <div className="h-48 relative overflow-hidden bg-black">
          {socialData.is_video ? (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:scale-110 transition-transform duration-500">
               <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-full flex items-center justify-center text-white">▶</div>
            </div>
          ) : (
            <img 
              src={socialData.media_urls[0]} 
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" 
              alt="Media content"
            />
          )}
          <div className="absolute top-3 left-3 bg-blue-600 text-[10px] uppercase font-bold px-2 py-1 rounded shadow-lg">
            {socialData.platform}
          </div>
        </div>
      )}

      <div className="p-6 space-y-4 flex-1 flex flex-col">
        <div className="space-y-1">
          <div className="text-[10px] text-zinc-500 font-mono overflow-hidden text-ellipsis whitespace-nowrap">{result.metadata.url}</div>
          <h4 className="font-bold text-lg leading-tight line-clamp-2 group-hover:text-blue-400 transition-colors">
            {isSocial && socialData?.post_text ? socialData.post_text.slice(0, 80) + '...' : result.metadata.title}
          </h4>
        </div>

        <p className="text-sm text-zinc-400 line-clamp-3">
          {result.metadata.description || result.paragraphs[0] || "No content extracted."}
        </p>

        <div className="pt-4 mt-auto flex items-center justify-between border-t border-white/5">
          <div className="flex gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-zinc-500">{result.links.length} Links</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-zinc-500">{Object.keys(result.headings).length} Heading Groups</span>
          </div>
          <a 
            href={result.metadata.url} 
            target="_blank" 
            className="text-blue-400 hover:scale-110 active:scale-95 transition-all"
            aria-label="View original site"
          >
            ↗
          </a>
        </div>
      </div>
    </article>
  );
}
