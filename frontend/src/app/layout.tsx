import type { Metadata } from 'next';
import 'katex/dist/katex.min.css';
import './globals.css';
import { ExperimentProvider } from '@/context/ExperimentContext';
import { Header } from '@/components/Header';
export const metadata: Metadata = { title: 'Optimisation Arena — Compare. Explore. Discover.', description: 'An interactive scientific workspace for comparing optimisation algorithms with measured experiments.' };
export default function RootLayout({ children }: {
    children: React.ReactNode;
}) { return <html lang="en"><body><ExperimentProvider><Header />{children}</ExperimentProvider></body></html>; }
