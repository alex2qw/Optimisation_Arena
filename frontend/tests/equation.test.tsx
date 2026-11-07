import { it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { Equation } from '../src/components/Equation';
import { report } from './contract';
it('renders the backend equation as accessible math', () => { const html = renderToStaticMarkup(<Equation latex={report.problem.equation_latex}/>); expect(html).toContain('katex'); expect(html).toContain('MathML'); expect(html).toContain('x'); });
