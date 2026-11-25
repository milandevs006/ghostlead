import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'GhostLead — Lead integrity', description: 'Lead integrity workspace', icons: { icon: [{url:'/brand/favicon.ico',type:'image/x-icon'},{url:'/brand/shield.png',type:'image/png'}], apple:'/brand/shield.png' } };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
