export default function SectionCard({
    title,
    children,
}) {
    return (
        <div className="bg-surface rounded-2xl border border-line p-6">

            <h2 className="font-display text-lg font-bold text-ink mb-4">
                {title}
            </h2>

            {children}

        </div>
    );
}
