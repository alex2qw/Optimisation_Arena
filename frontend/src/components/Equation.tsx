import katex from 'katex';
export function Equation({ latex }: {
    latex: string;
}) { return <span className="equation" dangerouslySetInnerHTML={{ __html: katex.renderToString(latex, { throwOnError: false, strict: 'ignore', trust: false, output: 'htmlAndMathml' }) }}/>; }
