"""Diagnostic plots for damping estimator validation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from scipy.signal import hilbert
from typing import cast

from wav_to_freq.domain.results import EstimateResult


def plot_td_envelope_diagnostic(
    y_filt: NDArray[np.float64],
    *,
    fs: float,
    estimate: EstimateResult,
    out_png: Path,
    transient_s: float = 0.20,
) -> Path:
    """Plot TD envelope fit diagnostic: envelope + log-fit + residuals."""

    fs = float(fs)
    y = np.asarray(y_filt, dtype=np.float64)
    analytic = hilbert(y)
    env = np.abs(cast(NDArray[np.complex128], analytic)).astype(np.float64)
    t = np.arange(y.size, dtype=np.float64) / fs

    # Extract fit window from diagnostics if available
    i0_fit = 0
    i1_fit = y.size
    fit_duration = estimate.diagnostics.get("env_fit_duration_s")
    if fit_duration and np.isfinite(fit_duration):
        i0_fit = int(round(transient_s * fs))
        i1_fit = min(y.size, i0_fit + int(round(float(fit_duration) * fs)))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    # Top: signal + envelope + fit window
    ax1.plot(t, y, label="Filtered response", alpha=0.5, linewidth=0.8)
    ax1.plot(t, env, label="Envelope", linewidth=1.5)
    if i0_fit < i1_fit:
        ax1.axvspan(
            t[i0_fit], t[i1_fit - 1], alpha=0.2, color="green", label="Fit window"
        )
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title("TD Envelope Fit")

    # Bottom: log-envelope + fit line
    eps = np.finfo(float).eps
    ln_env = np.log(np.clip(env, eps, None))
    ax2.plot(t, ln_env, label="log(envelope)", alpha=0.7)

    if i0_fit < i1_fit and estimate.zeta is not None:
        t_fit = t[i0_fit:i1_fit] - t[i0_fit]
        env_fit = env[i0_fit:i1_fit]
        ln_env_fit = np.log(np.clip(env_fit, eps, None))

        # Fit line
        m, c = np.polyfit(t_fit, ln_env_fit, 1)
        ln_hat = c + m * t_fit
        ax2.plot(t[i0_fit:i1_fit], ln_hat, "r--", label="Log-linear fit", linewidth=2)

        r2 = estimate.diagnostics.get("env_fit_r2")
        if r2 and np.isfinite(r2):
            ax2.text(
                0.95,
                0.95,
                f"R²={float(r2):.3f}",
                transform=ax2.transAxes,
                ha="right",
                va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("log(Amplitude)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png


def plot_fd_half_power_diagnostic(
    f: NDArray[np.float64],
    pxx: NDArray[np.float64],
    *,
    estimate: EstimateResult,
    out_png: Path,
) -> Path:
    """Plot FD half-power diagnostic: PSD with bandwidth markers and damping calculation."""

    f = np.asarray(f, dtype=np.float64)
    pxx = np.asarray(pxx, dtype=np.float64)
    db = 10.0 * np.log10(pxx + np.finfo(float).eps)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))

    # Top: full PSD with bandwidth markers
    ax1.plot(f, db, linewidth=1.5, label="PSD")

    fi_hz = estimate.fi_bin_hz
    f1_hz = estimate.diagnostics.get("f1_hz")
    f2_hz = estimate.diagnostics.get("f2_hz")

    if fi_hz and np.isfinite(fi_hz):
        idx = np.argmin(np.abs(f - fi_hz))
        ax1.axvline(
            fi_hz, color="r", linestyle="--", label=f"Peak: {fi_hz:.1f} Hz", linewidth=2
        )
        ax1.plot(f[idx], db[idx], "ro", markersize=8)

    if f1_hz and f2_hz and np.isfinite(f1_hz) and np.isfinite(f2_hz):
        ax1.axvline(
            float(f1_hz),
            color="g",
            linestyle=":",
            label=f"f₁: {float(f1_hz):.1f} Hz",
            linewidth=2,
        )
        ax1.axvline(
            float(f2_hz),
            color="g",
            linestyle=":",
            label=f"f₂: {float(f2_hz):.1f} Hz",
            linewidth=2,
        )

        # Half-power line
        if fi_hz:
            idx_peak = np.argmin(np.abs(f - fi_hz))
            half_power_db = db[idx_peak] - 3.0
            ax1.axhline(
                half_power_db,
                color="orange",
                linestyle=":",
                alpha=0.7,
                label="-3 dB line",
                linewidth=2,
            )

    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Power (dB)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title("FD Half-Power Bandwidth")

    # Bottom: zoomed view around peak showing damping calculation
    if (
        fi_hz
        and f1_hz
        and f2_hz
        and np.isfinite(fi_hz)
        and np.isfinite(f1_hz)
        and np.isfinite(f2_hz)
    ):
        # Zoom to ±50% around peak
        f_window = 0.5 * fi_hz
        mask = (f >= fi_hz - f_window) & (f <= fi_hz + f_window)
        if np.any(mask):
            f_zoom = f[mask]
            db_zoom = db[mask]

            ax2.plot(f_zoom, db_zoom, linewidth=2, label="PSD")
            ax2.axvline(
                fi_hz,
                color="r",
                linestyle="--",
                label=f"f_n = {fi_hz:.1f} Hz",
                linewidth=2,
            )

            idx_peak = np.argmin(np.abs(f - fi_hz))
            peak_db = db[idx_peak]
            half_power_db = peak_db - 3.0

            ax2.axhline(
                half_power_db, color="orange", linestyle=":", linewidth=2, label="-3 dB"
            )
            ax2.plot(
                [float(f1_hz), float(f2_hz)],
                [half_power_db, half_power_db],
                "go",
                markersize=10,
                label="Half-power points",
            )

            # Annotate bandwidth and damping
            bw_hz = float(f2_hz) - float(f1_hz)
            zeta_pct = estimate.zeta * 100.0 if estimate.zeta else 0.0

            ax2.annotate(
                "",
                xy=(float(f2_hz), half_power_db - 2),
                xytext=(float(f1_hz), half_power_db - 2),
                arrowprops=dict(arrowstyle="<->", color="purple", lw=2),
            )
            ax2.text(
                (float(f1_hz) + float(f2_hz)) / 2,
                half_power_db - 3.5,
                f"Δf = {bw_hz:.1f} Hz\nζ = Δf/(2f_n) = {zeta_pct:.1f}%",
                ha="center",
                va="top",
                fontsize=10,
                bbox=dict(boxstyle="round", facecolor="yellow", alpha=0.7),
            )

            ax2.set_xlabel("Frequency (Hz)")
            ax2.set_ylabel("Power (dB)")
            ax2.legend(loc="upper right")
            ax2.grid(True, alpha=0.3)
            ax2.set_title("Damping from Half-Power Bandwidth")

    plt.tight_layout()
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png


def plot_energy_decay_diagnostic(
    y_filt: NDArray[np.float64],
    *,
    fs: float,
    estimate: EstimateResult,
    out_png: Path,
    transient_s: float = 0.20,
) -> Path:
    """Plot energy decay diagnostic: energy curve + fit."""

    fs = float(fs)
    y = np.asarray(y_filt, dtype=np.float64)
    analytic = hilbert(y)
    env = np.abs(cast(NDArray[np.complex128], analytic)).astype(np.float64)
    energy = env**2
    t = np.arange(energy.size, dtype=np.float64) / fs

    # Extract fit window from diagnostics
    i0_fit = int(round(transient_s * fs))
    i1_fit = energy.size
    fit_duration = estimate.diagnostics.get("energy_fit_duration_s")
    if fit_duration and np.isfinite(fit_duration):
        i1_fit = min(energy.size, i0_fit + int(round(float(fit_duration) * fs)))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    # Top: energy curve
    ax1.plot(t, energy, label="Energy proxy", linewidth=1.5)
    if i0_fit < i1_fit:
        ax1.axvspan(
            t[i0_fit], t[i1_fit - 1], alpha=0.2, color="green", label="Fit window"
        )
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Energy")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title("Energy Decay")

    # Bottom: log-energy + fit
    eps = np.finfo(float).eps
    ln_energy = np.log(np.clip(energy, eps, None))
    ax2.plot(t, ln_energy, label="log(energy)", alpha=0.7)

    if i0_fit < i1_fit and estimate.zeta is not None:
        t_fit = t[i0_fit:i1_fit] - t[i0_fit]
        energy_fit = energy[i0_fit:i1_fit]
        ln_energy_fit = np.log(np.clip(energy_fit, eps, None))

        # Fit line
        m, c = np.polyfit(t_fit, ln_energy_fit, 1)
        ln_hat = c + m * t_fit
        ax2.plot(t[i0_fit:i1_fit], ln_hat, "r--", label="Log-linear fit", linewidth=2)

        r2 = estimate.diagnostics.get("energy_fit_r2")
        if r2 and np.isfinite(r2):
            ax2.text(
                0.95,
                0.95,
                f"R²={float(r2):.3f}",
                transform=ax2.transAxes,
                ha="right",
                va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("log(Energy)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png


def plot_filtered_response(
    y_filt: NDArray[np.float64],
    *,
    fs: float,
    fi_hz: float,
    out_png: Path,
) -> Path:
    """Plot filtered response for a specific peak."""

    fs = float(fs)
    y = np.asarray(y_filt, dtype=np.float64)
    t = np.arange(y.size, dtype=np.float64) / fs

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, y, linewidth=1.0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"Filtered Response (centered on {fi_hz:.1f} Hz)")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png
