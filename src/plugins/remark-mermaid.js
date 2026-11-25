// ```mermaid 코드 블록을 <pre class="mermaid">로 바꿔 expressive-code가 코드로 처리하지 않게 한다.
// 실제 그리기는 Layout.astro의 클라이언트 스크립트가 한다.
const escapeHtml = (s) =>
	s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function walk(node) {
	if (!node.children) return;
	node.children = node.children.map((child) => {
		if (child.type === "code" && child.lang === "mermaid") {
			return {
				type: "html",
				value: `<pre class="mermaid">${escapeHtml(child.value)}</pre>`,
			};
		}
		walk(child);
		return child;
	});
}

export function remarkMermaid() {
	return (tree) => walk(tree);
}
