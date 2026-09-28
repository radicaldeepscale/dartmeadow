/*
 * LEATR Live Cube - a slim, embeddable view of the Session Cube live feed.
 *
 * Drop onto any page:
 *   <div data-live-cube style="width:506px;height:506px"></div>
 *   <script src="live-cube.js" defer></script>
 *
 * Optional attributes on the element:
 *   data-href="https://cube.leatr.xyz" where a click goes
 *   data-target="_blank"               link target (default _blank)
 *   data-log="3"                       event log lines shown (0 hides it)
 *
 * Reads the same live table the Session Cube polls (config.json, then the
 * active maze's latest-export.json) and draws it the way the Session Cube's
 * buildModel() does, at the broadcast dimensions, with no layer spread:
 * frosted red wall panes (brighter where they line the walked path), the
 * blue path and event nodes along it. Like the Session Cube's play mode, a
 * traveler walks the path on a loop, lighting its trail and logging each
 * analytics event as it passes. Slow turntable; clicking opens the full
 * Session Cube.
 */
(function () {
  "use strict";

  var GAS =
    "https://script.google.com/macros/s/AKfycbyzkQxLR5miUXP6oDw-1AR1GIjgpzlw9iLw0gO_ZTeLfL849LWbNX7WVz_kf7yLWBKA_w/exec";
  var THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r132/three.min.js";
  var POLL_MS = 5000;
  var SPIN = 0.12; // rad/s turntable
  var WALK_SPEED = 28; // path steps/s, same as the Session Cube's play
  var COLORS = {
    corridor: "#ff5446",
    shell: "#d23c32",
    quiet: "#b3302a",
    path: "#3aa8ff",
    event: "#9fdcff",
    head: "#e6f6ff",
  };

  var FACE_STEP = {
    left: [-1, 0, 0],
    right: [1, 0, 0],
    bottom: [0, -1, 0],
    top: [0, 1, 0],
    back: [0, 0, -1],
    front: [0, 0, 1],
  };
  var FACES = ["right", "front", "top", "left", "back", "bottom"];

  function withThree(cb) {
    if (window.THREE && window.THREE.InstancedMesh) return cb(window.THREE);
    var s = document.createElement("script");
    s.src = THREE_URL;
    s.onload = function () {
      cb(window.THREE);
    };
    document.head.appendChild(s);
  }

  function readLive(path) {
    var url = GAS + "?action=ashread&path=" + encodeURIComponent(path) + "&t=" + Date.now();
    return fetch(url, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("proxy");
        return res.json();
      })
      .then(function (body) {
        if (body == null) return null;
        if (body.ok === false) throw new Error(body.error || "unread");
        if (body.ok === true && "content" in body) return body.content;
        return body;
      });
  }

  function fetchLive() {
    return readLive("ashtree/analytics-live/config.json").then(function (config) {
      if (!config || !config.enabled || !config.mazeId) return null;
      return readLive("ashtree/analytics-live/" + config.mazeId + "/latest-export.json").then(function (raw) {
        return raw && typeof raw === "object" && raw.cube && raw.cube.cells ? raw : null;
      });
    });
  }

  function key(x, y, z) {
    return x + "," + y + "," + z;
  }

  // Port of the Session Cube's buildModel(): walked path from layer 0 in
  // order, and each shared wall drawn once, classed by whether it lines the
  // path (corridor), sits on the outer shell, or neither (quiet).
  function buildModel(raw) {
    var cube = raw.cube;
    var layer = (raw.pathIndex && raw.pathIndex[0] && raw.pathIndex[0].path) || [];
    var path = layer.slice().sort(function (a, b) {
      return a.order - b.order;
    });
    var onPath = {};
    path.forEach(function (n) {
      onPath[key(n.x, n.y, n.z)] = 1;
    });
    var walls = { corridor: [], shell: [], quiet: [] };
    var w = cube.width;
    var h = cube.height;
    var d = cube.depth;
    cube.cells.forEach(function (cell) {
      if (!cell.walls) return;
      FACES.forEach(function (face) {
        if (!cell.walls[face]) return;
        if (face === "left" && cell.x !== 0) return;
        if (face === "back" && cell.z !== 0) return;
        if (face === "bottom" && cell.y !== 0) return;
        var s = FACE_STEP[face];
        var touches = onPath[key(cell.x, cell.y, cell.z)] || onPath[key(cell.x + s[0], cell.y + s[1], cell.z + s[2])];
        var shell =
          (face === "left" && cell.x === 0) ||
          (face === "right" && cell.x === w - 1) ||
          (face === "bottom" && cell.y === 0) ||
          (face === "top" && cell.y === h - 1) ||
          (face === "back" && cell.z === 0) ||
          (face === "front" && cell.z === d - 1);
        walls[touches ? "corridor" : shell ? "shell" : "quiet"].push([cell.x, cell.y, cell.z, s]);
      });
    });
    var events = [];
    path.forEach(function (n) {
      (n.events || []).forEach(function (e) {
        events.push(e);
      });
    });
    return { width: w, height: h, depth: d, path: path, walls: walls, events: events };
  }

  // A small random maze + walk so the cube is never empty while waiting.
  function demoRaw(n) {
    var cells = {};
    var all = [];
    for (var x = 0; x < n; x++)
      for (var y = 0; y < n; y++)
        for (var z = 0; z < n; z++) {
          var c = { x: x, y: y, z: z, walls: { left: true, right: true, top: true, bottom: true, front: true, back: true } };
          cells[key(x, y, z)] = c;
          all.push(c);
        }
    var opposite = { left: "right", right: "left", top: "bottom", bottom: "top", front: "back", back: "front" };
    var seen = {};
    var stack = [cells[key(0, 0, 0)]];
    var path = [];
    seen[key(0, 0, 0)] = 1;
    while (stack.length) {
      var cur = stack[stack.length - 1];
      path.push({ order: path.length, x: cur.x, y: cur.y, z: cur.z, events: [] });
      var options = [];
      for (var f in FACE_STEP) {
        var s = FACE_STEP[f];
        var nk = key(cur.x + s[0], cur.y + s[1], cur.z + s[2]);
        if (cells[nk] && !seen[nk]) options.push([f, cells[nk]]);
      }
      if (!options.length) {
        stack.pop();
        continue;
      }
      var pick = options[Math.floor(Math.random() * options.length)];
      cur.walls[pick[0]] = false;
      pick[1].walls[opposite[pick[0]]] = false;
      seen[key(pick[1].x, pick[1].y, pick[1].z)] = 1;
      stack.push(pick[1]);
    }
    return {
      cube: { width: n, height: n, depth: n, cells: all },
      totalEvents: 0,
      exportedAt: "demo",
      mode: "DEMO",
      pathIndex: [{ layer: 0, path: path.slice(0, Math.floor(path.length * 0.5)) }],
    };
  }

  function eventLine(e) {
    var label = String(e.label || "").replace(/_/g, " ");
    var detail = e.detail != null && e.detail !== "" ? " " + e.detail : "";
    var m = /T(\d{2}:\d{2}:\d{2})/.exec(e.ts || "");
    return (m ? m[1] + "  " : "") + label + detail;
  }

  function ditherTexture(THREE) {
    // 4x4 Bayer pattern -> frosted, dithered wall panes.
    var bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
    var px = 32;
    var cv = document.createElement("canvas");
    cv.width = cv.height = px;
    var g = cv.getContext("2d");
    var img = g.createImageData(px, px);
    for (var y = 0; y < px; y++)
      for (var x = 0; x < px; x++) {
        var t = bayer[(y % 4) * 4 + (x % 4)] / 16;
        var edge = x < 2 || y < 2 || x > px - 3 || y > px - 3;
        var i = (y * px + x) * 4;
        img.data[i] = img.data[i + 1] = img.data[i + 2] = 255;
        img.data[i + 3] = edge ? 255 : t < 0.45 ? 200 : 40;
      }
    g.putImageData(img, 0, 0);
    var tex = new THREE.CanvasTexture(cv);
    tex.magFilter = THREE.NearestFilter;
    tex.minFilter = THREE.NearestFilter;
    return tex;
  }

  function mount(el, THREE) {
    var href = el.getAttribute("data-href") || "https://cube.leatr.xyz";
    var target = el.getAttribute("data-target") || "_blank";
    var logLines = Math.max(0, parseInt(el.getAttribute("data-log") || "3", 10) || 0);

    if (getComputedStyle(el).position === "static") el.style.position = "relative";
    el.style.cursor = "pointer";
    el.setAttribute("role", "link");
    el.setAttribute("tabindex", "0");
    el.setAttribute("aria-label", "Open the LEATR Session Cube");
    el.title = "Open the LEATR Session Cube";

    var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    el.appendChild(renderer.domElement);

    var hud = document.createElement("div");
    hud.style.cssText =
      "position:absolute;left:10px;bottom:8px;right:10px;font:600 11px/1.45 ui-monospace,Menlo,monospace;" +
      "letter-spacing:.06em;color:#bfe6ff;text-shadow:0 1px 3px #000;pointer-events:none;text-align:left";
    var log = document.createElement("div");
    log.style.cssText = "font-weight:500;opacity:.85";
    var badge = document.createElement("div");
    badge.style.cssText = "display:flex;gap:6px;align-items:center";
    var dot = document.createElement("span");
    dot.style.cssText = "width:7px;height:7px;border-radius:50%;background:#8ea39a;display:inline-block";
    var label = document.createElement("span");
    label.textContent = "SESSION CUBE";
    badge.appendChild(dot);
    badge.appendChild(label);
    hud.appendChild(log);
    hud.appendChild(badge);
    el.appendChild(hud);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(32, 1, 0.1, 200);
    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    var sun = new THREE.DirectionalLight(0xffffff, 0.6);
    sun.position.set(3, 6, 4);
    scene.add(sun);

    var turntable = new THREE.Group();
    turntable.rotation.x = 0.18;
    scene.add(turntable);
    var content = new THREE.Group();
    turntable.add(content);

    var dither = ditherTexture(THREE);
    function paneMat(color, opacity) {
      return new THREE.MeshBasicMaterial({
        color: color,
        map: dither,
        transparent: true,
        opacity: opacity,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
    }
    var wallMats = { corridor: paneMat(COLORS.corridor, 0.5), shell: paneMat(COLORS.shell, 0.26), quiet: paneMat(COLORS.quiet, 0.16) };
    var pathMat = new THREE.MeshStandardMaterial({ color: COLORS.path, emissive: COLORS.path, emissiveIntensity: 0.55, roughness: 0.4 });
    var eventMat = new THREE.MeshStandardMaterial({ color: COLORS.event, emissive: COLORS.path, emissiveIntensity: 1.0 });
    var headMat = new THREE.MeshStandardMaterial({ color: COLORS.head, emissive: COLORS.path, emissiveIntensity: 1.4 });
    var linkMat = new THREE.LineBasicMaterial({ color: COLORS.path, transparent: true, opacity: 0.35 });
    var trailMat = new THREE.LineBasicMaterial({ color: COLORS.event, transparent: true, opacity: 0.95 });
    var travelerMat = new THREE.MeshBasicMaterial({ color: COLORS.head, depthTest: false });
    var haloMat = new THREE.MeshBasicMaterial({
      color: COLORS.path,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
    });
    var wallGeo = new THREE.PlaneGeometry(0.92, 0.92);
    var nodeGeo = new THREE.BoxGeometry(0.26, 0.26, 0.26);
    var eventGeo = new THREE.BoxGeometry(0.44, 0.44, 0.44);
    var headGeo = new THREE.BoxGeometry(0.56, 0.56, 0.56);
    var travelerGeo = new THREE.SphereGeometry(0.3, 16, 12);
    var haloGeo = new THREE.SphereGeometry(0.62, 16, 12);
    var shared = [wallGeo, nodeGeo, eventGeo, headGeo, travelerGeo, haloGeo];
    var head = null;
    var traveler = new THREE.Mesh(travelerGeo, travelerMat);
    var halo = new THREE.Mesh(haloGeo, haloMat);
    traveler.renderOrder = 10;
    halo.renderOrder = 11;
    // The walk: a traveler glides along the path at the Session Cube's play
    // speed and loops, lighting the trail behind it and logging each
    // event node as it passes.
    var walk = { pts: [], events: [], trail: null, step: 0, index: -1, flare: 0 };
    var lastKey = "";
    var lastDims = "";

    function clear() {
      while (content.children.length) {
        var child = content.children.pop();
        if (child.geometry && shared.indexOf(child.geometry) === -1) child.geometry.dispose();
        if (child.dispose) child.dispose();
      }
      head = null;
    }

    function frame(model) {
      var dims = model.width + "x" + model.height + "x" + model.depth;
      if (dims === lastDims) return;
      lastDims = dims;
      var span = Math.max(model.width, model.height, model.depth);
      camera.position.set(0, span * 1.1, span * 2.9);
      camera.lookAt(0, 0, 0);
    }

    function build(raw) {
      var model = buildModel(raw);
      var cx = (model.width - 1) / 2;
      var cy = (model.height - 1) / 2;
      var cz = (model.depth - 1) / 2;
      clear();
      frame(model);

      var m = new THREE.Object3D();
      ["quiet", "shell", "corridor"].forEach(function (kind) {
        var list = model.walls[kind];
        if (!list.length) return;
        var mesh = new THREE.InstancedMesh(wallGeo, wallMats[kind], list.length);
        list.forEach(function (f, i) {
          var s = f[3];
          m.position.set(f[0] - cx + s[0] * 0.5, f[1] - cy + s[1] * 0.5, f[2] - cz + s[2] * 0.5);
          m.rotation.set(0, 0, 0);
          if (s[0]) m.rotation.y = Math.PI / 2;
          else if (s[1]) m.rotation.x = Math.PI / 2;
          m.updateMatrix();
          mesh.setMatrixAt(i, m.matrix);
        });
        content.add(mesh);
      });

      var path = model.path;
      if (path.length) {
        var plain = [];
        var marked = [];
        path.forEach(function (n) {
          (n.events && n.events.length ? marked : plain).push(n);
        });
        [
          [plain, nodeGeo, pathMat],
          [marked, eventGeo, eventMat],
        ].forEach(function (set) {
          if (!set[0].length) return;
          var mesh = new THREE.InstancedMesh(set[1], set[2], set[0].length);
          set[0].forEach(function (n, i) {
            m.position.set(n.x - cx, n.y - cy, n.z - cz);
            m.rotation.set(0, 0, 0);
            m.updateMatrix();
            mesh.setMatrixAt(i, m.matrix);
          });
          content.add(mesh);
        });
        var pts = [];
        for (var i = 1; i < path.length; i++) {
          var a = path[i - 1];
          var b = path[i];
          if (Math.abs(a.x - b.x) + Math.abs(a.y - b.y) + Math.abs(a.z - b.z) !== 1) continue;
          pts.push(new THREE.Vector3(a.x - cx, a.y - cy, a.z - cz), new THREE.Vector3(b.x - cx, b.y - cy, b.z - cz));
        }
        if (pts.length) content.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), linkMat));
        walk.pts = path.map(function (n) {
          return new THREE.Vector3(n.x - cx, n.y - cy, n.z - cz);
        });
        walk.events = path.map(function (n) {
          return n.events || [];
        });
        walk.trail = new THREE.Line(new THREE.BufferGeometry().setFromPoints(walk.pts), trailMat);
        walk.trail.geometry.setDrawRange(0, 0);
        content.add(walk.trail);
        if (walk.step >= walk.pts.length - 1) walk.step = 0;
        walk.index = Math.floor(walk.step) - 1;
        content.add(halo);
        content.add(traveler);
        var last = path[path.length - 1];
        head = new THREE.Mesh(headGeo, headMat);
        head.position.set(last.x - cx, last.y - cy, last.z - cz);
        content.add(head);
      }

    }

    function logEvent(e) {
      if (!logLines) return;
      var line = document.createElement("div");
      line.textContent = eventLine(e);
      log.appendChild(line);
      while (log.childNodes.length > logLines) log.removeChild(log.firstChild);
    }

    function advance(dt) {
      var pts = walk.pts;
      if (pts.length < 2) return;
      var limit = pts.length - 1;
      walk.step += dt * WALK_SPEED;
      if (walk.step >= limit) {
        walk.step = 0;
        walk.index = -1;
        log.innerHTML = "";
      }
      var i = Math.floor(walk.step);
      var f = walk.step - i;
      for (var k = walk.index + 1; k <= i; k++) {
        if (walk.events[k].length) {
          walk.events[k].forEach(logEvent);
          walk.flare = 1;
        }
      }
      walk.index = i;
      traveler.position.lerpVectors(pts[i], pts[Math.min(i + 1, limit)], f);
      halo.position.copy(traveler.position);
      walk.trail.geometry.setDrawRange(0, i + 2);
      walk.flare = Math.max(0, walk.flare - dt * 2.5);
      travelerMat.color.set(walk.flare > 0.05 ? COLORS.head : COLORS.event);
      haloMat.color.set(walk.flare > 0.05 ? COLORS.head : COLORS.path);
    }

    function setStatus(live, text) {
      dot.style.background = live ? COLORS.path : "#8ea39a";
      dot.style.boxShadow = live ? "0 0 8px " + COLORS.path : "none";
      label.textContent = text;
    }

    var hasLive = false;
    function poll() {
      fetchLive()
        .then(function (raw) {
          if (!raw) {
            setStatus(false, hasLive ? "SESSION CUBE \u00b7 PAUSED" : "SESSION CUBE");
            return;
          }
          hasLive = true;
          var c = raw.cube;
          setStatus(true, "LIVE \u00b7 " + c.width + "\u00d7" + c.height + "\u00d7" + c.depth + " \u00b7 " + (raw.totalEvents || 0) + " EVENTS");
          var path = (raw.pathIndex && raw.pathIndex[0] && raw.pathIndex[0].path) || [];
          var k = raw.exportedAt + "|" + raw.totalEvents + "|" + path.length;
          if (k === lastKey) return;
          lastKey = k;
          build(raw);
        })
        .catch(function () {
          setStatus(false, hasLive ? "SESSION CUBE \u00b7 RECONNECTING" : "SESSION CUBE");
        });
    }
    build(demoRaw(5));
    poll();
    setInterval(function () {
      if (!document.hidden) poll();
    }, POLL_MS);

    function resize() {
      var r = el.getBoundingClientRect();
      var width = Math.max(1, r.width);
      var height = Math.max(1, r.height || r.width);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    resize();
    if (window.ResizeObserver) new ResizeObserver(resize).observe(el);
    else window.addEventListener("resize", resize);

    var visible = true;
    if (window.IntersectionObserver)
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
      }).observe(el);

    var prev = performance.now();
    function tick(now) {
      var dt = Math.max(0, Math.min(0.1, (now - prev) / 1000));
      prev = now;
      if (visible && !document.hidden) {
        turntable.rotation.y += SPIN * dt;
        advance(dt);
        halo.scale.setScalar(1 + walk.flare * 0.9 + Math.sin(now / 310) * 0.1);
        if (head) {
          var s = 1 + Math.sin(now / 320) * 0.14;
          head.scale.set(s, s, s);
        }
        renderer.render(scene, camera);
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);

    function go() {
      window.open(href, target, target === "_blank" ? "noopener" : undefined);
    }
    el.addEventListener("click", go);
    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        go();
      }
    });
  }

  function start() {
    var els = document.querySelectorAll("[data-live-cube]");
    if (!els.length) return;
    withThree(function (THREE) {
      for (var i = 0; i < els.length; i++) {
        if (els[i]._liveCubeMounted) continue;
        els[i]._liveCubeMounted = true;
        mount(els[i], THREE);
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
