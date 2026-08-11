# References for the machine-certification method

*Versioned companion of the Geometric Function Atlas website document `data/proofs/REFERENCES.md` at source commit acee553e03f9ca2bdcb55977e18ff7d9deb57e40. All citations were verified by the website authors to a DOI / publisher / arXiv record; the package ships the document unchanged except for this header.*



## A. Structural reduction (exact, no truncation)

This is the part that turns "for every f in S\*(φ)…" into a finite polynomial
inequality on a compact box — with no sampling and no series truncation.

- **I. Schur (1917).** *Über Potenzreihen, die im Innern des Einheitskreises beschränkt sind.* J. reine angew. Math. 147, 205–232 (Part II: 148 (1918), 122–145).
  DOI: https://doi.org/10.1515/crll.1917.147.205 · **readable modern treatment (free): Li & Sugawa (2019), *Schur parameters and Carathéodory class*, https://arxiv.org/abs/1902.02000** (the original eudml scan is access-restricted; Li–Sugawa give the parametrization in usable form).
  *→ §2.2: the Schur-parameter map sends the closed polydisc exactly onto the admissible Schwarz-coefficient body — the lemma `schur-onto-coefficient-body`. We use the classical factored formulas, not a truncation.*

- **B. Simon (2005).** *Orthogonal Polynomials on the Unit Circle* (OPUC), Parts 1–2. AMS Colloquium Publications 54.
  https://bookstore.ams.org/coll-54 · errata: http://math.caltech.edu/opuc.html
  *→ §2.2: modern, rigorous grounding of Schur parameters / Verblunsky coefficients used in the exactness argument.*

- **C. Foias & A. E. Frazho (1990).** *The Commutant Lifting Approach to Interpolation Problems.* Operator Theory: Adv. & Appl. 44, Birkhäuser.
  DOI: https://doi.org/10.1007/978-3-0348-7712-1
  *→ §2.2: operator-theoretic statement that the Schur parametrization is onto — "nothing admissible is missed, nothing spurious added."*

- **Carathéodory–Toeplitz coefficient body** (functions with positive real part, |cₙ| ≤ 2). Consolidated in U. Grenander & G. Szegő, *Toeplitz Forms and Their Applications* (Univ. California Press, 1958) and Duren §2 (below).
  Reference entry: https://encyclopediaofmath.org/wiki/Carath%C3%A9odory_class
  *→ §2: the coefficient region underlying the Schwarz/Schur body (φ paints a region; zf′/f must live in it).*

- **R. J. Libera & E. J. Złotkiewicz (1982, 1983).** *Early coefficients of the inverse of a regular convex function*, Proc. AMS 85, 225–230, https://doi.org/10.1090/S0002-9939-1982-0652447-5 · *Coefficient bounds for the inverse of a function with derivative in P*, Proc. AMS 87, 251–257, https://doi.org/10.1090/S0002-9939-1983-0681830-8
  *→ HARDNESS §4: the analytic c₂,c₃-in-terms-of-c₁ representations that human proofs use to drop dimension before search — the prerequisite for machine-certifying H₃(1)/Zalcman-class bounds.*

- **P. L. Duren (1983).** *Univalent Functions.* Grundlehren 259, Springer (subordination: ch. 6).
  https://link.springer.com/book/9780387907956 · (alt.: C. Pommerenke, *Univalent Functions*, 1975)
  *→ §2.1: the subordination principle f ≺ g and the membership characterization zf′/f ≺ φ.*

- **W. C. Ma & D. Minda (1994).** *A unified treatment of some special classes of univalent functions.* Proc. Conf. Complex Analysis (Tianjin, 1992), Conf. Proc. Lecture Notes Anal. I, 157–169, International Press.
  Series: https://www.intlpress.com/site/pub/pages/series/0017/index.php (no DOI; not openly hosted)
  *→ The class S\*(φ) itself — the entire catalogue of 27 classes the engine proves over.*

---

## B. Rigorous arithmetic (the enclosures are true bounds, not estimates)

- **R. E. Moore (1966).** *Interval Analysis.* Prentice-Hall. — and the modern text: **R. E. Moore, R. B. Kearfott & M. J. Cloud (2009).** *Introduction to Interval Analysis.* SIAM. DOI: https://doi.org/10.1137/1.9780898717716
  *→ §3: the foundational rigorous-enclosure model the prover is built on.*

- **IEEE Std 754-2019**, *IEEE Standard for Floating-Point Arithmetic.* DOI: https://doi.org/10.1109/IEEESTD.2019.8766229 — **N. J. Higham (2002).** *Accuracy and Stability of Numerical Algorithms*, 2nd ed., SIAM. DOI: https://doi.org/10.1137/1.9780898718027 — expository: **D. Goldberg (1991, Xerox PARC).** *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* ACM Comput. Surv. 23(1), 5–48. DOI: https://doi.org/10.1145/103162.103163
  *→ §3 (prover): every float64 op is widened by its IEEE-754 forward-error bound (~4·2⁻⁵² per op), so each computed interval rigorously encloses the true value — the lemma `ieee754-forward-error`.*

- **J. L. D. Comba & J. Stolfi (1993).** *Affine Arithmetic and its Applications to Computer Graphics.* Proc. VI SIBGRAPI, 9–18. https://www.inf.ufrgs.br/~comba/papers/abstract/comba93.htm — survey: **L. H. de Figueiredo & J. Stolfi (2004).** *Affine Arithmetic: Concepts and Applications.* Numer. Algorithms 37, 147–158. DOI: https://doi.org/10.1023/B:NUMA.0000049462.70970.b6 — project page: https://ic.unicamp.br/~stolfi/EXPORT/projects/affine-arith/Welcome.html
  *→ §4 / HARDNESS §2–3: the affine-arithmetic bound form (tracks linear correlations exactly), including the trig-correlated form where cos tₖ and sin tₖ share the angle's noise symbol.*

- **The dependency problem** — Moore–Kearfott–Cloud (2009, above) and **A. Neumaier (1990),** *Interval Methods for Systems of Equations*, Cambridge UP (https://arnold-neumaier.at/interval.html).
  *→ §4 ("the dependency lesson"): why we evaluate the **factored, hash-consed DAG** rather than the expanded polynomial — (1−r₀²) computed once annihilates everything it multiplies; the v1 killer box went 1.6×10⁻² → 7.6×10⁻¹⁴.*

- **F. Johansson and contributors.** *mpmath — arbitrary-precision floating-point arithmetic* (Python). https://mpmath.org · https://github.com/mpmath/mpmath · Zenodo DOI: https://doi.org/10.5281/zenodo.1476881
  *→ §3 (checker) / §5: `mpmath.iv` independently re-verifies each leaf certificate in arbitrary precision — the prover/checker split.*

---

## C. Verified global optimization (the branch-and-bound bound family)

- **A. Neumaier (2004).** *Complete Search in Continuous Global Optimization and Constraint Satisfaction.* Acta Numerica 13, 271–369. **Free PDF: https://arnold-neumaier.at/ms/glopt03.pdf** — canonical book treatment: **E. Hansen & G. W. Walster (2004),** *Global Optimization Using Interval Analysis*, 2nd ed., Marcel Dekker.
  *→ §4: interval branch-and-bound over the polar box; also the **monotonicity test** (sign-definite gradient ⇒ optimum on a face — our "monotonicity slide").*

- **Centered / mean-value form** — Moore (1966); analyzed in **H. Cornelius & R. Lohner (1984),** *Computing the range of values of real functions with accuracy higher than second order*, Computing 33, 331–347. DOI: https://doi.org/10.1007/BF02242276
  *→ §4.2: the first-order centered bound form, P(mid) + Σ max|∂ᵥP|·hᵥ.*

- **K. Makino & M. Berz (2003).** *Taylor Models and Other Validated Functional Inclusion Methods.* Int. J. Pure Appl. Math. 4(4), 379–456. https://www.bmtdynamics.org/pub/papers/TMIJPAM03/TMIJPAM03.pdf
  *→ §4.3: the second-order Taylor bound form — the one that converges at attained maxima on boundary faces.*

- **T. Csendes & D. Ratz (1997).** *Subdivision Direction Selection in Interval Methods for Global Optimization.* SIAM J. Numer. Anal. 34(3), 922–938. DOI: https://doi.org/10.1137/S0036142995281528 — **R. B. Kearfott (1996).** *Rigorous Global Search: Continuous Problems.* Kluwer. DOI: https://doi.org/10.1007/978-1-4757-2495-0
  *→ §4: gradient-aware / "smear"-based bisection — split the dimension whose smear term actually blocks certification (HARDNESS confirms it is per-box optimal, beating "widest dim" by 2.5×).*

---

## D. The classical results & reductions we mechanize

- **M. Fekete & G. Szegő (1933).** *Eine Bemerkung über ungerade schlichte Funktionen.* J. London Math. Soc. s1-8(2), 85–89. DOI: https://doi.org/10.1112/jlms/s1-8.2.85
  *→ The functional |a₃ − μa₂²|.*

- **F. R. Keogh & E. P. Merkes (1969).** *A coefficient inequality for certain classes of analytic functions.* Proc. AMS 20(1), 8–12. DOI: https://doi.org/10.1090/S0002-9939-1969-0232926-9 · open PDF: https://www.ams.org/journals/proc/1969-020-01/S0002-9939-1969-0232926-9/
  *→ `gft/sharp.py`, lemma `fekete-szego-single-harmonic`: the single-angle reduction that closes the Fekete–Szegő bracket to a point in closed form (no branch-and-bound, no slack).*

- **Ch. Pommerenke (1966, 1967).** *On the coefficients and Hankel determinants of univalent functions*, J. London Math. Soc. s1-41, 111–122, https://doi.org/10.1112/jlms/s1-41.1.111 · *On the Hankel determinants of univalent functions*, Mathematika 14, 108–112, https://doi.org/10.1112/S002557930000807X
  *→ The Hankel-determinant functionals H₂(2)=a₂a₄−a₃² and H₃(1).*

- **B. Kowalczyk, A. Lecko & D. K. Thomas (2022).** *The sharp bound of the third Hankel determinant for starlike functions.* Forum Math. 34(5), 1249–1254. DOI: https://doi.org/10.1515/forum-2021-0308
  *→ The target result H₃(1) ≤ 4/9, and (HARDNESS §4) the by-hand dimension-reduction strategy whose machine analogue is our next milestone.*

- **Zalcman conjecture** (never published by Zalcman; canonical first print) **J. E. Brown & A. Tsao (1986),** *On the Zalcman conjecture for starlike and typically real functions*, Math. Z. 191, 467–474, https://doi.org/10.1007/BF01162720 — **S. L. Krushkal (2010),** *Proof of the Zalcman conjecture for initial coefficients*, Georgian Math. J. 17, 663–681, https://doi.org/10.1515/gmj.2010.043
  *→ The Zalcman functional |a₃²−a₅| (m=4 — currently out of reach, HARDNESS §2).*

- **V. Ravichandran & Shelly Verma (2017).** *Generalized Zalcman conjecture for some classes of analytic functions.* J. Math. Anal. Appl. 450(1), 592–605. DOI: https://doi.org/10.1016/j.jmaa.2017.01.053 (online-first 2016; corpus paper #407)
  *→ The generalized Zalcman functional |aₙaₘ − a_{n+m−1}| ≤ (n−1)(m−1). Engine keys `zalcman_a2a3_a4` (|a₂a₃−a₄|, m=3) and `zalcman_a2a4_a5` (|a₂a₄−a₅|, m=4). We machine-certify the (2,3) bound ≤ 2 for S\* (independent certificate of their result); the Ma-Minda / order-α extensions have interior non-clean maxima and remain OPEN conjectures, and the (2,4) m=4 case is deferred to the heavy box.*

- **L. de Branges (1985).** *A proof of the Bieberbach conjecture.* Acta Math. 154, 137–152. DOI: https://doi.org/10.1007/BF02392821 · open: https://projecteuclid.org/journals/acta-mathematica/volume-154/issue-1-2/A-proof-of-the-Bieberbach-conjecture/10.1007/BF02392821.full
  *→ Background (EXPLAINER §1): |aₙ| ≤ n — the field's archetypal "find the exact edge" result.*

- **Logarithmic coefficients γₙ** (log(f/z) = 2·Σ γₙ zⁿ). Definition and the sharp |γₙ| ≤ 1/n for starlike functions (Koebe extremal): Duren §3 (above). Modern study (the Hankel-of-log-coefficients direction): **B. Kowalczyk & A. Lecko (2022),** *Second Hankel determinant of logarithmic coefficients of convex and starlike functions*, Bull. Aust. Math. Soc. 105(3), 458–467. DOI: https://doi.org/10.1017/S0004972721000836
  *→ `gft/proofs.py` `_functional_expr` keys `log_gamma2`, `log_gamma3`: γₙ is an exact polynomial in a₂…a₅, so the same reduction/B&B handles it; γ₂ is m=2 and closes in closed form (proven-exact), giving |γ₂| = 1/2 for S\*.*

- **Inverse coefficients Aₙ** (f⁻¹(w) = w + Σ Aₙ wⁿ). Extremal values from the inverse Koebe function (A₂=2, A₃=5, A₄=14, …): **K. Löwner (1923),** *Untersuchungen über schlichte konforme Abbildungen des Einheitskreises. I*, Math. Ann. 89, 103–121, DOI: https://doi.org/10.1007/BF01448091 — and, for subclasses, Libera–Złotkiewicz (§A above).
  *→ `gft/proofs.py` `_functional_expr` keys `inv_a3`, `inv_a4`: Aₙ is an exact polynomial in a₂…a₅; |A₃| = |2a₂²−a₃| = |a₃ − 2a₂²| is Fekete–Szegő at μ=2, so the m=2 closed form proves it exact (|A₃| = 5 for S\*).*

---

## E. Roadmap — methods we discuss but have NOT shipped

*Listed for honesty: the production engine is interval branch-and-bound (Sections
B–C). None of the following is in it today. They are the candidate routes to
close the m=4 gap (HARDNESS §2, §4) — certified dimension reduction, then an
algebraic-certificate optimizer.*

- **J. B. Lasserre (2001).** *Global Optimization with Polynomials and the Problem of Moments.* SIAM J. Optim. 11(3), 796–817. DOI: https://doi.org/10.1137/S1052623400366802 — the moment-SOS hierarchy.
- **P. A. Parrilo (2003).** *Semidefinite programming relaxations for semialgebraic problems.* Math. Program. 96(2), 293–320. DOI: https://doi.org/10.1007/s10107-003-0387-5 (thesis: https://thesis.library.caltech.edu/1647/) — SOS relaxations.
- **M. Putinar (1993).** *Positive polynomials on compact semi-algebraic sets.* Indiana Univ. Math. J. 42(3), 969–984. DOI: https://doi.org/10.1512/iumj.1993.42.42045 — the Positivstellensatz the SOS certificate rests on.
- **J. Wang, V. Magron & J. B. Lasserre (2021).** *TSSOS: A Moment-SOS Hierarchy That Exploits Term Sparsity.* SIAM J. Optim. 31(1), 30–58. DOI: https://doi.org/10.1137/19M1307871 (arXiv:1912.08899) — sparsity-exploiting SOS for higher dimension.
- **J. Garloff (1985/86).** *Convergent Bounds for the Range of Multivariate Polynomials.* In *Interval Mathematics 1985*, LNCS 212, 37–56. DOI: https://doi.org/10.1007/3-540-16437-5_5 — Bernstein-form range enclosures (an alternative to the Taylor bound family).
