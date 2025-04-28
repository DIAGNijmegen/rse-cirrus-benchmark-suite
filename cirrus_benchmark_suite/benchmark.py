import statistics
from datetime import datetime

from playwright.sync_api import expect, sync_playwright
from scipy.stats import norm

from cirrus_benchmark_suite import evaluate
from cirrus_benchmark_suite.history import BenchmarkHistory
from cirrus_benchmark_suite.session import (
    create_viewer_session,
    do_permission_checks,
    login,
    permission_check,
)
from cirrus_benchmark_suite.utils import (
    DEBUG,
    Timer,
    get_cirrus_version,
    get_git_hash,
    new_page,
)

# Quick globals
offset_ms = None


def get_base_line_loading(ctx, n=10):
    """Determine the baseline loading offset to base statistics on."""
    times = []
    for _ in range(n):
        with Timer() as timer:
            with new_page(ctx) as page:
                page.goto("about:blank")
        times.append(timer.elapsed_time)

    return statistics.mean(times), statistics.stdev(times)


def _format(metric):
    return int(round(metric, 0))


def _correct(metric):
    if offset_ms is None:
        raise RuntimeError("No offset ms for page loading has been calculated")
    return _format(metric - offset_ms)


def gen_benchmark_metadata(page):
    return {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "suite_git_commit": get_git_hash(),
        "CIRRUS_version": get_cirrus_version(page),
    }


@permission_check(
    "https://grand-challenge.org/api/v1/reader-studies/1e5946ed-46f8-4501-92fb-d85c91fa853c/"
)
def benchmark_reader_study(benchmarks, page, session_url):
    reader_study_url = f"{session_url}reader-study/1e5946ed-46f8-4501-92fb-d85c91fa853c/?config=2077fa74-9976-415f-8772-06801eb3d3e3"

    with Timer() as timer:
        page.goto(reader_study_url)

        # 1. Answer a question
        expect(
            page.get_by_role("button", name="Save and continue")
        ).to_be_visible(timeout=30_000)

        # 2. View an image
        expect(page.locator('[data-test="viewitem"]')).to_have_count(2)

    benchmarks["readerstudy.loading_first_case"] = _correct(timer.elapsed_time)

    # Wait 5 seconds to allow from some pre-loading
    page.wait_for_timeout(5000)

    page.locator("#reader-study-switcher-next-button").click()
    ok_button = page.get_by_role("button", name="Ok")

    with Timer() as timer:
        ok_button.click()

        # 1. Case information
        expect(page.get_by_text("This is friendly geezer")).to_be_visible()

        # 2. New image loaded
        expect(page.locator('[data-test="viewitem"]')).to_have_count(1)

    benchmarks["readerstudy.navigate_to_second_case"] = _format(
        timer.elapsed_time
    )  # Note: not offsetting for page loading here


@permission_check(
    "https://grand-challenge.org/api/v1/algorithms/jobs/82faf859-0d3d-4b6b-813c-804a86bd398c"
)
def benchmark_algorithm_job(benchmarks, page, session_url):
    algorihm_job_url = f"{session_url}algorithm-job/82faf859-0d3d-4b6b-813c-804a86bd398c?config=e0114bc8-1f0c-4f9f-b921-6c8f1e1ef850"
    with Timer() as timer:
        page.goto(algorihm_job_url)

        # 1. Annotations statistics
        expect(
            page.locator('[data-plugin-name="AnnotationStatisticsPlugin"]')
        ).to_be_visible(timeout=20_000)

        # 2. View annotations
        expect(
            page.locator('[data-plugin-name="AnnotationListPlugin"]')
        ).to_be_visible()

        # 3. View an image
        expect(page.locator('[data-test="viewitem"]')).to_have_count(2)

    benchmarks["algorithmjob.loading"] = _correct(timer.elapsed_time)


@permission_check(
    "https://grand-challenge.org/api/v1/archives/items/72166e13-d52b-4fa8-ab3a-bea1e02d5bc4"
)
def benchmark_archive_item(benchmarks, page, session_url):
    archive_item_url = (
        f"{session_url}archive-item/72166e13-d52b-4fa8-ab3a-bea1e02d5bc4"
    )
    with Timer() as timer:
        page.goto(archive_item_url)

        # 1. View annotations
        expect(
            page.locator('[data-plugin-name="AnnotationListPlugin"]')
        ).to_be_visible(timeout=20_000)

        # 2. Overlay plugin
        expect(
            page.locator('[data-plugin-name="OverlayPlugin"]')
        ).to_be_visible(timeout=20_000)

        # 3. View  images
        expect(page.locator('[data-test="viewitem"]')).to_have_count(4)

    benchmarks["archiveitem.loading"] = _correct(timer.elapsed_time)


def benchmark(ctx, session_url):
    benchmarks = {}

    with new_page(ctx) as page:
        benchmark_reader_study(benchmarks, page, session_url)

    with new_page(ctx) as page:
        benchmark_algorithm_job(benchmarks, page, session_url)

    with new_page(ctx) as page:
        benchmark_archive_item(benchmarks, page, session_url)

    return benchmarks


def setup(ctx):
    with new_page(ctx) as page:
        login(page)

        # Ensure a session is running
        session_url = create_viewer_session(page)

        # Re-use page to get metdata
        metadata = gen_benchmark_metadata(page)

        # Early detection of permission problems
        do_permission_checks(page)

    return session_url, metadata


def report(history, evaluation):
    for column in history.metrics.columns:
        print(f"## {column}")
        if column not in evaluation.p_values:
            print("Skipped: no new data point")
            continue
        print(f"### Runtime: {history.latest[column]}ms")
        print(f"P-value: {evaluation.p_values[column]*100:0.3f}%")
        print(
            "\tProbability of getting this runtime under the assumption that it is from the reference distribution: a low value suggests an outlier."
        )
        print(f"Reference distribution (N={evaluation.n_history[column]}):")

        mean = evaluation.means[column]
        sem = evaluation.sem[column]
        print(f"Average±SEM: {mean:0.0f}±{sem:0.0f}ms")
        print(f"33rd Percentile: {norm.ppf(0.33, loc=mean, scale=sem):0.0f}ms")
        print(f"66th Percentile: {norm.ppf(0.66, loc=mean, scale=sem):0.0f}ms")
        print("\n---")


def test():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not DEBUG)
        try:
            ctx = browser.new_context()

            session_url, metadata = setup(ctx)

            global offset_ms
            offset_ms, stdev_ms = get_base_line_loading(ctx)
            print(f"Base-line page loading: {offset_ms:.0f}±{stdev_ms:.0f}ms")

            benchmarks = benchmark(ctx, session_url)

            history = BenchmarkHistory()
            history.update_with(
                {
                    **metadata,
                    **benchmarks,
                }
            )

            eval = evaluate.evaluate(history.metrics)

            report(history, eval)

        finally:
            ctx.close()
            browser.close()
            playwright = None


if __name__ == "__main__":
    with Timer() as timer:
        test()
    runtime = timer.elapsed_time / 1000

    print("Benchmarking finished!")
    print(f"Total runtime: {runtime:0.1f} seconds")
