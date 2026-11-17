#!/usr/bin/env python
"""Generate demo/extraction_source.pdf — the demo's stand-in 'paper'.

The real Reynolds 2006 article is paywalled and cannot be redistributed, so the
demo cannot ship the publisher's PDF. This script renders a one-page *model
specification sheet* — our own restatement of the model's equations and
parameter values (which are facts, not copyrightable expression), with the full
citation — so the PDF -> Antimony -> validation pipeline can be demonstrated end
to end from a file anyone can read.

Run it to (re)generate the PDF:

    python demo/make_extraction_source.py
"""

from pathlib import Path

SHEET = r"""REYNOLDS 2006 - REDUCED MODEL OF THE ACUTE INFLAMMATORY RESPONSE
Model specification sheet  (demo extraction source)

SOURCE
  Reynolds A, Rubin J, Clermont G, Day J, Vodovotz Y, Ermentrout GB.
  A reduced mathematical model of the acute inflammatory response:
  I. Derivation of model and analysis of anti-inflammation.
  J. Theor. Biol. 242(1):220-236, 2006.  doi:10.1016/j.jtbi.2006.02.016
  Curated SBML: BioModels BIOMD0000000714.

  NOTE: one-page restatement of the model (equations + parameter values are
  facts) so the extraction pipeline can be shown without redistributing the
  publisher's copyrighted PDF. Values cross-checked against the curated SBML.

STATE VARIABLES
  P      pathogen load
  Nstar  activated phagocytes (neutrophils / macrophages)
  D      tissue damage
  C_A    anti-inflammatory mediators (cortisol, IL-10)

AUXILIARY TERMS  (anti-inflammatory down-modulation)
  f(Nstar) = Nstar / (1 + (C_A/c_inf)^2)
  R        = (k_nn*Nstar + k_np*P + k_nd*D) / (1 + (C_A/c_inf)^2)
  g        = (Nstar + k_cnd*D) / (1 + (C_A/c_inf)^2)

GOVERNING EQUATIONS
  dP/dt     = k_pg*P*(1 - P/p_inf) - k_pm*s_m*P/(mu_m + k_mp*P) - k_pn*f(Nstar)*P
  dNstar/dt = s_nr*R/(mu_nr + R) - mu_n*Nstar
  dD/dt     = k_dn * f(Nstar)^6/(x_dn^6 + f(Nstar)^6) - mu_d*D
  dC_A/dt   = s_c + k_cn * g/(1 + g) - mu_c*C_A

PARAMETERS
  k_pg=0.3   p_inf=20    k_pm=0.6    s_m=0.005   mu_m=0.002  k_mp=0.01
  k_pn=1.8   s_nr=0.08   mu_nr=0.12  mu_n=0.05   k_nn=0.01   k_np=0.1
  k_nd=0.02  k_dn=0.35   x_dn=0.06   mu_d=0.02   s_c=0.0125  k_cn=0.04
  k_cnd=48   mu_c=0.1    c_inf=0.28

INITIAL CONDITIONS  (baseline; time in hours)
  P=1   Nstar=0   D=0   C_A=0.125

VALIDATION SCENARIOS  (published outcomes read at t = 500 h)
  healthy:        P(0)=0.5  ->  P=0,  Nstar=0,      D=0,      C_A=0.125
  aseptic death:  P(0)=1.5  ->  P=0,  Nstar=0.635,  D=17.40,  C_A=0.523
  Threshold: outcome flips between P(0)=1.0 (healthy) and 1.2 (aseptic death).
"""


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    out = Path(__file__).resolve().parent / "extraction_source.pdf"
    with PdfPages(out) as pdf:
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(
            0.06,
            0.97,
            SHEET,
            family="monospace",
            fontsize=8.2,
            va="top",
            ha="left",
        )
        pdf.savefig(fig)
        plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
