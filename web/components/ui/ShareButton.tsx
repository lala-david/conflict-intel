"use client";

import { useState } from "react";
import { Share2, Check, Twitter, Link } from "lucide-react";

interface Props {
  title: string;
  url?: string;
}

export function ShareButton({ title, url }: Props) {
  const [copied, setCopied] = useState(false);
  const shareUrl = url || (typeof window !== "undefined" ? window.location.href : "");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn("Clipboard write failed:", err);
    }
  };

  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(shareUrl)}`;

  return (
    <div className="flex items-center gap-2">
      <a
        href={twitterUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-md border border-border p-2 text-text-dim transition hover:bg-surface-2 hover:text-text-primary"
        title="Share on X"
      >
        <Twitter className="h-4 w-4" />
      </a>
      <button
        onClick={handleCopy}
        className="rounded-md border border-border p-2 text-text-dim transition hover:bg-surface-2 hover:text-text-primary"
        title="Copy link"
      >
        {copied ? (
          <Check className="h-4 w-4 text-cat-counterterrorism" />
        ) : (
          <Link className="h-4 w-4" />
        )}
      </button>
    </div>
  );
}
