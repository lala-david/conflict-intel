import Link from "next/link";
import { Header } from "@/components/layout/Header";

export default function NotFound() {
  return (
    <>
      <Header />
      <main className="flex min-h-[60vh] flex-col items-center justify-center px-6">
        <h1 className="font-display text-8xl font-bold text-text-dim">404</h1>
        <p className="mt-4 text-lg text-text-dim">Page not found</p>
        <Link
          href="/"
          className="mt-8 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
        >
          Back to home
        </Link>
      </main>
    </>
  );
}
