"""Self-contained reproduction of the interval certificates in Theorem 4.8 of
the Experimental Mathematics paper on the Geometric Function Atlas:

  (a) R(phi_S  -> phi_R) = arcsin(3 - 2*sqrt 2),   phi_S(u)  = 1 + sin u
  (b) R(phi_SG -> phi_R) = (1/2) log 2,            phi_SG(u) = 2/(1+e^{-u})

phi_R(z) = 1 + z(k+z)/(k(k-z)),  k = 1+sqrt 2,  rho = 1/k = sqrt 2 - 1.

Libraries: sympy (exact algebra, symbolic derivatives) and mpmath.iv
(outward-rounded interval arithmetic, mpmath >= 1.3).  Precision:
mp.dps = 60 for point values, iv.dps = 30 for all interval evaluations.

Parts
  0. Algebra: eliminate t from A = t(1+t)/(1-t), |t| = rho, and compare with
     eq. (Fpoly); confirm phi_R(z) - 1 = g(z/k), g(t) = t(1+t)/(1-t);
     y-parity of F; the contact point is a cusp (singular point of F = 0).
  1. Symmetry reduction to theta in [0, pi].
  2. Bulk: interval lower bound of H(theta) = F(Re A(r e^{i theta}),
     Im A(r e^{i theta})) on N boxes covering [0, pi - delta].
  3. Endpoint: H(pi) = 0, H'(pi) = 0 exactly (sympy), and an interval lower
     bound of H'' on [pi - delta, pi] (single box, as in the paper, and
     subdivided).  Then H(theta) >= (c/2)(pi - theta)^2 > 0 there.

The radius r is enclosed rigorously: r = [r_lo, r_hi] is certified to contain
the true radius by interval evaluation of the defining equation (sin r = eta,
resp. tanh(r/2) = eta, eta = 3 - 2 sqrt 2) at r_lo and r_hi.  Theta boxes are
built from iv.pi, so they cover [0, pi - delta] and [pi - delta, pi] exactly.

Run:  python examples/em_paper/thm48_interval_check.py      (about a minute)
"""
# ruff: noqa: UP031  (percent formatting kept verbatim from the paper script)
import time

import mpmath as mpm
import sympy as sp
from mpmath import iv, mp

mp.dps = 60
iv.dps = 30

T0 = time.time()
x, y, t, th, A, Ab = sp.symbols("x y t theta A Abar")
X, Y = sp.symbols("X Y", real=True)
RHO = sp.sqrt(2) - 1
K = 1 + sp.sqrt(2)
ETA = 3 - 2 * sp.sqrt(2)


def F_paper(xx, yy, r):
    q = xx**2 + yy**2
    return (-r**8 + r**6 * (q + 2 * xx + 1) + r**4 * (2 * xx * q + 6 * q + 2 * xx)
            + r**2 * (q**2 + 2 * xx * q + q) - q**2)


# ---------------------------------------------------------------- part 0
print("== Part 0: algebra of the target")
rs = sp.Symbol("rho", positive=True)
P1 = t**2 + (1 + A) * t - A                      # A(1-t) = t(1+t)
P2 = sp.expand(-Ab * t**2 + (1 + Ab) * rs**2 * t + rs**4)   # conj eq. with tbar = rho^2/t
res = sp.expand(sp.resultant(P1, P2, t).subs({A: X + sp.I * Y, Ab: X - sp.I * Y}))
Fp = sp.expand(F_paper(X, Y, rs))
ratio = sp.simplify(res / Fp)
print("  resultant_t(P1, P2) / F_paper =", ratio)
assert ratio.free_symbols == set(), "F_paper is not a constant multiple of the resultant"

z = sp.Symbol("z")
g = lambda s: s * (1 + s) / (1 - s)
phiR_minus_1 = z * (K + z) / (K * (K - z))
print("  phi_R(z) - 1 - g(z/k) =", sp.simplify(phiR_minus_1 - g(z / K)),
      " (so |z|=1 <-> |t|=1/k=rho)")
print("  F(x,-y) - F(x,y) =", sp.expand(F_paper(X, -Y, RHO) - F_paper(X, Y, RHO)),
      " (F depends on y only through y^2)")
F = sp.expand(F_paper(X, Y, RHO))
Fx, Fy = sp.diff(F, X), sp.diff(F, Y)
at_c = {X: -ETA, Y: 0}
print("  F, F_x, F_y at A0=-(3-2sqrt2):",
      [sp.nsimplify(sp.simplify(e.subs(at_c))) for e in (F, Fx, Fy)],
      " -> A0 is a singular point of F=0")
gp = sp.simplify(sp.diff(g(t), t))
print("  g'(t) =", sp.factor(gp), "; g'(-rho) =", sp.simplify(gp.subs(t, -RHO)),
      "; g(-rho) =", sp.simplify(g(-RHO)), "; g''(-rho) =",
      sp.simplify(sp.diff(g(t), t, 2).subs(t, -RHO)))
print("  F(0,0) =", sp.nsimplify(sp.simplify(F.subs({X: 0, Y: 0}))), "=",
      sp.N(F.subs({X: 0, Y: 0}), 8))
# leftmost point of the target boundary g(rho e^{is})
mp.dps = 30
bx = [(mpm.re(mpm.mpf(RHO.evalf(40)) * mpm.expj(s) * (1 + mpm.mpf(RHO.evalf(40)) * mpm.expj(s))
       / (1 - mpm.mpf(RHO.evalf(40)) * mpm.expj(s))), s) for s in mpm.linspace(0, 2 * mpm.pi, 20001)]
mn = min(bx)
print("  min Re of target boundary A = %.10f at arg t = %.6f (A0 = %.10f)"
      % (mn[0], mn[1], -float(ETA)))
print("  F(-1/4, 1/10) =", sp.N(F.subs({X: -sp.Rational(1, 4), Y: sp.Rational(1, 10)}), 6),
      "> 0 (inside, left of A0);  F(-1/4, 0) =", sp.N(F.subs({X: -sp.Rational(1, 4), Y: 0}), 6),
      "< 0 (outside): A0 is the tip of an inward cusp, not the left end of the target")
mp.dps = 60

# ---------------------------------------------------------------- symbolic H
# u = r e^{i theta} = a + i b.
rr = sp.Symbol("r", positive=True)
a, b = rr * sp.cos(th), rr * sp.sin(th)
SOURCES = {
    # (a) A = sin u = sin a cosh b + i cos a sinh b
    "sine": (sp.sin(a) * sp.cosh(b), sp.cos(a) * sp.sinh(b), sp.asin(ETA), sp.Rational(1, 20)),
    # (b) A = phi_SG(u) - 1 = tanh(u/2) = (sinh a + i sin b)/(cosh a + cos b)
    "sigmoid": (sp.sinh(a) / (sp.cosh(a) + sp.cos(b)), sp.sin(b) / (sp.cosh(a) + sp.cos(b)),
                sp.log(2) / 2, sp.Rational(1, 100)),
}

# check the tanh form symbolically
u = sp.Symbol("u")
print("  2/(1+e^{-u}) - 1 - tanh(u/2) =", sp.simplify((2 / (1 + sp.exp(-u)) - 1 - sp.tanh(u / 2)).rewrite(sp.exp)))

IVMOD = {
    "sin": iv.sin, "cos": iv.cos, "exp": iv.exp, "sqrt": iv.sqrt,
    "sinh": lambda v: (iv.exp(v) - iv.exp(-v)) / 2,
    "cosh": lambda v: (iv.exp(v) + iv.exp(-v)) / 2,
}


def LO(v):
    """exact lower endpoint of an interval, as an mpf"""
    return mp.make_mpf(v._mpi_[0])


def HI(v):
    return mp.make_mpf(v._mpi_[1])


def ivfun(expr, args):
    return sp.lambdify(args, expr, modules=[IVMOD, "mpmath"])


def rho_iv():
    return iv.sqrt(2) - 1


def enclose_radius(name):
    """Return an interval certified to contain the true radius."""
    eps = mpm.mpf(10) ** -25
    if name == "sine":
        r0 = mpm.asin(3 - 2 * mpm.sqrt(2))
        f = lambda rv: iv.sin(rv) - (3 - 2 * iv.sqrt(2))       # increasing in r
    else:
        r0 = mpm.log(2) / 2
        f = lambda rv: (iv.exp(rv) - 1) / (iv.exp(rv) + 1) - (3 - 2 * iv.sqrt(2))  # tanh(r/2)-eta
    lo, hi = iv.mpf(r0 - eps), iv.mpf(r0 + eps)
    assert HI(f(lo)) < 0 < LO(f(hi)), "radius enclosure failed"
    return iv.mpf([lo.a, hi.b])


def run(name, N=2000, N_end=50):
    xe, ye, rexact, delta = SOURCES[name]
    print("\n== Theorem 4.8(%s): source %s, r = %s, delta = %s" % ("a" if name == "sine" else "b",
                                                                   name, rexact, delta))
    # --- part 1: symmetry
    print("  Part 1: x(-theta) = x(theta):", sp.simplify(xe.subs(th, -th) - xe) == 0,
          "; y(-theta) = -y(theta):", sp.simplify(ye.subs(th, -th) + ye) == 0)
    print("          => H(-theta) = H(theta) since F is even in y; theta in [0,pi] suffices")

    # --- exact endpoint facts
    H = F.subs({X: xe, Y: ye})
    xpi, ypi = [sp.simplify(e.subs(th, sp.pi).subs(rr, rexact)) for e in (xe, ye)]
    Hpi = sp.nsimplify(sp.simplify(sp.expand(F.subs({X: xpi, Y: ypi}))))
    # H'(pi) = F_x x' + F_y y'; exact evaluation
    xp, yp = sp.diff(xe, th), sp.diff(ye, th)
    xpp, ypp = sp.diff(xp, th), sp.diff(yp, th)
    Hp_pi = sp.simplify((Fx.subs({X: xpi, Y: ypi}) * xp.subs(th, sp.pi)
                         + Fy.subs({X: xpi, Y: ypi}) * yp.subs(th, sp.pi)).subs(rr, rexact))
    print("  A(-r) =", xpi, "+ i*", ypi, " (= -(3-2sqrt2)?)", sp.simplify(xpi + ETA) == 0)
    print("  H(pi) =", Hpi, ";  H'(pi) =", sp.nsimplify(Hp_pi))

    # --- symbolic H'' via chain rule (sympy), then interval-evaluate
    Fxx, Fxy, Fyy = sp.diff(F, X, 2), sp.diff(F, X, Y), sp.diff(F, Y, 2)
    Hpp_sym = Fxx * xp**2 + 2 * Fxy * xp * yp + Fyy * yp**2 + Fx * xpp + Fy * ypp
    # sanity: chain-rule form equals direct second derivative (spot check)
    chk = (sp.diff(H, th, 2) - Hpp_sym.subs({X: xe, Y: ye})).subs({rr: rexact, th: sp.Rational(3, 1)})
    print("  |d2H/dtheta2 (direct) - chain-rule form| at theta=3:", float(abs(sp.N(chk, 40))))

    # Interval evaluation uses F in the nested form of eq. (Fpoly) with rho
    # passed as an interval (expanding rho^k into a+b*sqrt2 causes massive
    # interval cancellation).  Partials are sympy derivatives of that form.
    Fg = F_paper(X, Y, rs)
    fx_ = ivfun(xe, (rr, th)); fy_ = ivfun(ye, (rr, th))
    Fiv = ivfun(Fg, (X, Y, rs))
    derivs = [ivfun(e, (rr, th)) for e in (xp, yp, xpp, ypp)]
    parts = [ivfun(e, (X, Y, rs)) for e in (sp.diff(Fg, X), sp.diff(Fg, Y), sp.diff(Fg, X, 2),
                                             sp.diff(Fg, X, Y), sp.diff(Fg, Y, 2))]
    RH = rho_iv()

    R = enclose_radius(name)
    print("  certified radius enclosure r in [%s, %s]" % (mpm.nstr(LO(R), 28), mpm.nstr(HI(R), 28)))

    def H_iv(T):
        return Fiv(fx_(R, T), fy_(R, T), RH)

    def Hpp_iv(T):
        X_, Y_ = fx_(R, T), fy_(R, T)
        xp_, yp_, xpp_, ypp_ = [d(R, T) for d in derivs]
        fx, fy, fxx, fxy, fyy = [p(X_, Y_, RH) for p in parts]
        return fxx * xp_**2 + 2 * fxy * xp_ * yp_ + fyy * yp_**2 + fx * xpp_ + fy * ypp_

    # --- part 2: bulk
    t1 = time.time()
    dl = iv.mpf(1) / int(1 / delta)
    stop = iv.pi - dl
    grid = [stop * i / N for i in range(N + 1)]
    grid[0] = iv.mpf(0)
    minlo, argmin = None, None
    for i in range(N):
        T = iv.mpf([grid[i].a, grid[i + 1].b])     # hull: covers [0, pi-delta]
        v = H_iv(T)
        if minlo is None or LO(v) < minlo:
            minlo, argmin = LO(v), i
    print("  bulk min lower bound (raw):", mpm.nstr(minlo, 8), "box", argmin)
    assert minlo > 0, "bulk certificate FAILED"
    print("  Part 2: N=%d boxes on [0, pi-%s]: certified min lower bound = %s (box %d), %.1fs"
          % (N, delta, mpm.nstr(minlo, 6), argmin, time.time() - t1))

    # --- part 3: endpoint second derivative
    t1 = time.time()
    one = Hpp_iv(iv.mpf([(iv.pi - dl).a, iv.pi.b]))
    edges = [iv.pi - dl + dl * j / N_end for j in range(N_end + 1)]
    sub = min(LO(Hpp_iv(iv.mpf([edges[j].a, edges[j + 1].b]))) for j in range(N_end))
    assert LO(one) > 0 and sub > 0, "endpoint certificate FAILED"
    # true minimum of H'' on the endpoint interval (point evaluation, not a certificate)
    Hpp_num = sp.lambdify(th, Hpp_sym.subs({X: xe, Y: ye}).subs(rr, rexact), "mpmath")
    mp.dps = 30
    true_min = min(Hpp_num(mpm.pi - mpm.mpf(delta.p) / delta.q * (1 - mpm.mpf(j) / 2000))
                   for j in range(2001))
    mp.dps = 60
    print("  Part 3: H'' on [pi-%s, pi]: single-box lower bound = %s; %d-box lower bound = %s;"
          " sampled min = %s  (%.1fs)" % (delta, mpm.nstr(LO(one), 6), N_end, mpm.nstr(sub, 6),
                                          mpm.nstr(true_min, 7), time.time() - t1))
    # sampled bulk minimum (not a certificate)
    Hnum = sp.lambdify(th, H.subs(rr, rexact), "mpmath")
    mp.dps = 30
    s_min = min(Hnum((mpm.pi - mpm.mpf(delta.p) / delta.q) * j / 20000) for j in range(20001))
    mp.dps = 60
    print("          sampled min of H on [0, pi-delta] (20001 points, not a certificate) = %s"
          % mpm.nstr(s_min, 6))
    return minlo, LO(one), sub


out = {}
for nm in ("sine", "sigmoid"):
    out[nm] = run(nm)

print("\nSummary (iv.dps = %d, mp.dps = %d, mpmath %s, sympy %s):" % (iv.dps, mp.dps, mpm.__version__, sp.__version__))
for nm, (bulk, one, sub) in out.items():
    print("  %-8s bulk lower bound %s | H'' single-box %s | H'' 50-box %s"
          % (nm, mpm.nstr(bulk, 4), mpm.nstr(one, 4), mpm.nstr(sub, 4)))
print("Total runtime %.1fs" % (time.time() - T0))
