import type {Metadata} from 'next';
import './globals.css';
import { Toaster } from "@/components/ui/toaster"
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })


export const metadata: Metadata = {
  title: 'Neon Surf | Find Videos & GIFs',
  description: 'Search for videos and GIFs with a vibrant neon-themed interface. Features history and local favorites.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <main className="min-h-screen flex flex-col items-center py-6 px-4">
          {children}
        </main>
        <Toaster />
      </body>
    </html>
  );
}
