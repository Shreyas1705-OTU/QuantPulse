export default function MetricCard({
    title,
    value,
    unit,
    icon,
}) {
    return (
        <div className="bg-surface rounded-2xl border border-line p-6">

            <div className="flex justify-between items-center">

                <div>

                    <p className="text-muted text-sm">
                        {title}
                    </p>

                    <h2 className="font-display text-3xl font-bold mt-2 text-ink">
                        {value}
                        <span className="text-lg ml-1">
                            {unit}
                        </span>
                    </h2>

                </div>

                <div className="p-3 rounded-xl bg-accent-soft">
                    {icon}
                </div>

            </div>

        </div>
    );
}
