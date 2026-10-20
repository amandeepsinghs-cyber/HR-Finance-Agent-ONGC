import './globals.css';
import React from 'react';

export const metadata = {
  title: 'ONGC HR & Finance | Voice-to-Chart Spike',
  description: 'FastAPI + ADK Gemini Live bidi-streaming voice-to-chart prototype',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
