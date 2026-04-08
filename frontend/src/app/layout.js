import './globals.css';

export const metadata = {
  title: 'ReviewInsight — AI-Powered Product Review Analysis',
  description:
    'Paste any product URL and get instant AI-powered sentiment analysis, key themes, and actionable insights from customer reviews.',
  keywords: ['review analysis', 'sentiment analysis', 'AI', 'product reviews', 'NLP'],
  openGraph: {
    title: 'ReviewInsight',
    description: 'AI-Powered Product Review Analysis',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
