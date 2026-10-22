import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Yukti AI — ONGC HR & Finance Executive Intelligence',
  description: 'Voice-first AI agent for ONGC leadership (CMD, Director HR, Director Finance). Hands-free executive analytics, statutory policy guidance, and document generation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased font-sans min-h-screen">
        {children}
      </body>
    </html>
  );
}
