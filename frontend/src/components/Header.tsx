'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity } from 'lucide-react';
export function Header() { const path = usePathname(); return <header><Link className="brand" href="/"><span className="logo"><Activity size={30}/></span><div><strong>Optimisation Arena</strong><small>Compare algorithms. Understand the maths. Find the best solution.</small></div></Link><nav aria-label="Main navigation">{[['/experiments', 'Experiments'], ['/documentation', 'Documentation'], ['/about', 'About']].map(([href, text]) => <Link key={href} href={href} aria-current={path === href ? 'page' : undefined}>{text}</Link>)}</nav></header>; }
