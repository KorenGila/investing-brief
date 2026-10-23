/* Scenario engine. Mirrors scripts/scen2.py. Needs a global D (data_engine.json). */
var ENG = (function () {
  function interp(c, T) {
    var X = D.TEN;
    if (T <= X[0]) return c[0];
    for (var i = 1; i < X.length; i++) if (T <= X[i]) return c[i - 1] + (c[i] - c[i - 1]) * (T - X[i - 1]) / (X[i] - X[i - 1]);
    return c[c.length - 1];
  }
  function price(c, T, y) {
    if (T <= 1e-9) return 100;
    var n = Math.ceil(T * 2 - 1e-9), acc = n - T * 2, i = y / 200, cf = c / 2, s = 0, t;
    for (var k = 1; k <= n; k++) { t = k - acc; s += cf * Math.pow(1 + i, -t); }
    return s + 100 * Math.pow(1 + i, -t) - cf * acc;
  }
  function rungs(f) {
    var n = Math.round((f.hi - f.lo) * 12), r = [];
    for (var k = 0; k <= n; k++) r.push(f.lo + (f.hi - f.lo) * k / n);
    return r;
  }
  function nq(n) { return Math.max(1, Math.round(4 * n)); }
  function mean(a, s, e) { var t = 0; for (var i = s; i < e; i++) t += a[i]; return t / (e - s); }
  function tpLoad(n) {
    var tp = D.tp;
    if (n >= 10) return n === 10 ? 1 : D.P.l30;
    if (n < 1) return tp[0] / tp[9] * n;
    var i = Math.floor(n), fr = n - i, lo = tp[i - 1] / tp[9], hi = tp[Math.min(i, 9)] / tp[9];
    return lo + fr * (hi - lo);
  }
  function fedDev(dpi, du, drs) {
    var P = D.P, d = new Array(P.nq).fill(0);
    for (var t = 1; t <= 4; t++) { var r = t / 4; d[t] = P.rho * d[t - 1] + (1 - P.rho) * (drs * r + P.bpi * dpi * r + P.bdu * du * r); }
    var Dh = d[4];
    for (t = 5; t < P.nq; t++) d[t] = drs + (Dh - drs) * Math.exp(-P.kd * (t - 4) / 4);
    return d;
  }
  /* Structural model: macro surprises -> yield surprises at each tenor (vs today's forward path). */
  function modelSurprise(m) {
    var d = fedDev(m.dpi, m.du, m.drs);
    return { surp: D.TEN.map(function (n) { return mean(d, 4, 4 + nq(n)) + m.dtp * tpLoad(n); }), ffH: D.M[4] + d[4], dev: d };
  }
  /* Analog method: surprises at the short end, 2, 10 and 30 years -> every tenor. */
  function analogSurprise(sff, s2, s10, s30) {
    return D.TEN.map(function (n) {
      if (n <= 0.5) return sff;
      if (n === 1) return (sff + s2) / 2;
      if (n <= 2) return s2;
      if (n <= 10) return s2 + (s10 - s2) * (n - 2) / 8;
      return s10 + (s30 - s10) * (n - 10) / 20;
    });
  }
  /* 12-month returns: curve moves linearly to (today + roll + surprise); funds are monthly-rebalanced ladders. */
  function returns(surp) {
    var dy = D.TEN.map(function (n, i) { return D.ROLL[i] + surp[i]; });
    var curves = [];
    for (var s = 0; s <= 12; s++) curves.push(D.TODAY.map(function (v, i) { return v + dy[i] * s / 12; }));
    var res = {}, inc = 0;
    for (s = 0; s < 12; s++) {
      var mid = curves[s].map(function (v, i) { return (v + curves[s + 1][i]) / 2; });
      inc += (interp(mid, 1 / 12) + interp(mid, 0.25)) / 2;
    }
    res.SGOV = inc / 12 + D.SG.basis - D.SG.fee;
    ['SHY', 'IEF', 'TLT'].forEach(function (k) {
      var f = D.FUNDS[k], R = rungs(f), tot = 1;
      for (var s = 0; s < 12; s++) {
        var acc = 0;
        for (var j = 0; j < R.length; j++) {
          var T = R[j], y0 = interp(curves[s], T) + f.spread, y1 = interp(curves[s + 1], Math.max(T - 1 / 12, 1 / 12)) + f.spread;
          var cp = f.cpn === null ? y0 : f.cpn, p0 = price(cp, T, y0);
          acc += (price(cp, T - 1 / 12, y1) - p0 + cp / 12) / p0;
        }
        tot *= 1 + acc / R.length;
      }
      res[k] = (tot - 1) * 100 - f.fee;
    });
    return { ret: res, dy: dy };
  }
  function duration(k) {
    var f = D.FUNDS[k], R = rungs(f), t = 0;
    R.forEach(function (T) {
      var y = interp(D.TODAY, T) + f.spread, cp = f.cpn === null ? y : f.cpn, p = price(cp, T, y);
      t += (price(cp, T, y - 0.01) - price(cp, T, y + 0.01)) / 0.02 / p * 100;
    });
    return t / R.length;
  }
  return { interp: interp, price: price, modelSurprise: modelSurprise, analogSurprise: analogSurprise, returns: returns, duration: duration, fedDev: fedDev };
})();
