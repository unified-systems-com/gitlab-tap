/**
 * GitLab deployment — one placed picture of a self-managed GitLab as it is deployed
 * (req-gitlab-layout; drawn on /gitlab, reusable by any page whose scene holds GitLab nodes).
 *
 * The scene is whatever the panel's searches return. Nothing here names an entity id or an
 * instance: every placement is derived from the vocabulary's own edges, so the module draws a
 * design seed, a collected deployment, or several instances side by side the same way.
 *
 *   ┌──────────────────────── GitLab instance ─────────────────────────┐
 *   │ Ingress      Compute (by where it runs)   Data stores   Sign-in │   Trusted IdPs /
 *   │ [ALB]  ───▶  ┌ ECS service ┐              [RDS]          & audit │   event sinks
 *   │ [NLB]  ───▶  │ webservice  │ ───────────▶ [ElastiCache]  [SSO]──┼─▶ [Okta]
 *   │              │ workhorse   │              [S3 × n]       [audit]┼─▶ [S3]
 *   │              └─────────────┘              [EBS] [secret]        │
 *   │              Runners: ┌ ECS service ┐ ──▶ [job cluster]  [runner]│
 *   └──────────────────────────────────────────────────────────────────┘
 *
 * Containment:
 *   - service ⊃ process: RUNS_ON_SERVICE__gitlab, read directly by the nesting runtime (the
 *     process is the child, the service it runs on the parent).
 *   - instance ⊃ everything its deployment reaches: synthetic `_GITLAB_DEPLOYS` edges this
 *     module adds on every entry (and removes on re-entry). Ownership is derived from edges (graph
 *     node data carries no model fields): a process, runner, sign-in provider or audit destination
 *     belongs to the instance that RUNS_COMPONENT / REGISTERS_RUNNER / AUTHENTICATES_VIA_PROVIDER /
 *     STREAMS_AUDIT_EVENTS it; a runner manager to the instance of the runner it authenticates as;
 *     a foreign node (an ECS service, an RDS instance, a bucket, a load balancer) to the instance of
 *     the GitLab process on the other end of its edge. A node two instances share is drawn in the
 *     first and reported as a warning.
 *
 * Bands are decided by the edge that reached a node, never by its type, so an open end (an RDS
 * instance here, a self-hosted PostgreSQL elsewhere) lands in the right band either way. A node
 * the rules do not place is still drawn, in a row under the picture, and reported — never dropped.
 *
 * Standard tap layout module: `export async function execute(context)`
 * (spec-viz-layouts.md, req-viz-layout-module-contract).
 */

import {projectNested} from "/static/tap_viz/js/runtime/nested-projection.js";
import {applyStandardChrome, placeParentLabels, parentLabelInset} from "/static/tap_viz/js/runtime/chrome.js";

const T = {
    instance: "gitlab__gitlab_instance",
    component: "gitlab__gitlab_component",
    gitaly: "gitlab__gitaly_node",
    manager: "gitlab__runner_manager",
    runner: "gitlab__gitlab_runner",
    sso: "gitlab__sso_provider",
    audit: "gitlab__audit_event_destination",
};
const PROCESS_TYPES = new Set([T.component, T.gitaly, T.manager]);

const E = {
    runsComponent: "RUNS_COMPONENT__gitlab",
    registersRunner: "REGISTERS_RUNNER__gitlab",
    runsOn: "RUNS_ON_SERVICE__gitlab",
    db: "QUERIES_DATABASE__gitlab",
    redis: "CALLS_REDIS__gitlab",
    objects: "STORES_OBJECTS__gitlab",
    volume: "STORES_REPOSITORIES_ON_VOLUME__gitlab",
    secret: "READS_SECRET__gitlab",
    asRunner: "AUTHENTICATES_AS_RUNNER__gitlab",
    jobs: "LAUNCHES_JOB_TASKS__gitlab",
    viaProvider: "AUTHENTICATES_VIA_PROVIDER__gitlab",
    samlIdp: "TRUSTS_SAML_IDP__gitlab",
    oidcIssuer: "TRUSTS_ISSUER__identity_core",
    streams: "STREAMS_AUDIT_EVENTS__gitlab",
    delivers: "DELIVERS_EVENTS__gitlab",
    routes: "ROUTES_TRAFFIC__aws_core",
};
//: Data-store edges, in the order their targets stack in the data band.
const DATA_EDGES = [E.db, E.redis, E.volume, E.objects, E.secret];
//: Edges whose far end sits outside the instance box (someone else's system).
const OUTSIDE_EDGES = [E.samlIdp, E.oidcIssuer, E.delivers];

//: Which component is drawn first in the compute band (the request path, then the rest).
const COMPONENT_ORDER = ["workhorse", "webservice", "gitlab_shell", "registry", "kas", "pages", "sidekiq",
    "mailroom", "exporter", "toolbox", "migrations"];

const SYN = {deploys: "_GITLAB_DEPLOYS", label: "_gitlab_band_label"};
const SYN_CLASS = "gitlab-synthetic";

const GEOM = {
    leaf: {width: 150, height: 54},
    instanceFloor: {width: 400, height: 240},
    colGap: 90,
    rowGap: 26,
    bandLabelHeight: 26,
    instanceGap: 160,
    outsideGap: 120,
    labelInset: 14,
    dataWrap: 6,
};

const _containerPadding = (inset) => ({top: 12 + inset, right: 22, bottom: 20, left: 22});
const _instancePadding = (inset) => ({top: 22 + inset, right: 40, bottom: 36, left: 40});

export async function execute(context) {
    const {cy} = context;
    const warnings = [];
    const warn = (category, message) => {
        warnings.push({category, message});
        console.warn(`[gitlab deployment] ${category}: ${message}`);
    };

    _clear(cy);
    const instances = cy.nodes(`[entity_type = "${T.instance}"]`).sort((a, b) => _label(a).localeCompare(_label(b)));
    if (instances.empty()) {
        warn("gitlab_no_instance", "no GitLab instance in the scene; nothing to lay out");
        return {warnings};
    }

    const plan = _plan(cy, instances, warn);
    _addDeploys(cy, plan);

    const chrome = applyStandardChrome(cy, {leafMaxWidth: GEOM.leaf.width - 20});
    const inset = parentLabelInset({...chrome, inset: GEOM.labelInset});
    const baseSizes = {};
    cy.nodes().forEach((n) => { baseSizes[n.data("entity_type") || ""] = GEOM.leaf; });
    baseSizes[T.instance] = GEOM.instanceFloor;
    plan.serviceTypes.forEach((t) => { baseSizes[t] = GEOM.leaf; });

    const nested = await projectNested(cy, {
        relationships: [
            {name: "instance-deploys", gryphon: `(parent:${T.instance})-[:${SYN.deploys}]->(child)`},
            {name: "service-runs", gryphon: `(parent)<-[:${E.runsOn}]-(child)`},
        ],
        baseSizes,
        padding: 20,
        paddings: Object.fromEntries([...plan.serviceTypes].map((t) => [t, _containerPadding(inset)])),
        innerLayout: {name: "flow", gap: 24, sort: "input"},
    });
    warnings.push(...(nested.warnings || []));

    let x = 0;
    const outsideColumnX = [];
    instances.forEach((inst) => {
        const box = _placeInstance(cy, inst, plan.bands.get(inst.id()), x, 0, inset);
        outsideColumnX.push({inst, right: x + box.width});
        x += box.width + GEOM.instanceGap + (plan.outside.get(inst.id()).length ? GEOM.leaf.width + GEOM.outsideGap : 0);
    });
    outsideColumnX.forEach(({inst, right}) => _placeOutside(cy, inst, plan.outside.get(inst.id()), right));
    _placeLeftovers(cy, plan.leftovers, warn);

    placeParentLabels(cy, {
        anchor: "upper-left", inset: GEOM.labelInset,
        parentFontSize: chrome.parentFontSize, parentFontWeight: chrome.parentFontWeight,
    });
    _style(cy);
    return {warnings};
}

// ---------------------------------------------------------------------------
// Planning: who belongs to which instance, and in which band
// ---------------------------------------------------------------------------

function _plan(cy, instances, warn) {
    const owner = new Map();        // node id -> instance id
    const claim = (node, instId, why) => {
        if (!instId || node.empty()) return;
        const prior = owner.get(node.id());
        if (prior && prior !== instId) {
            warn("gitlab_shared_node", `${_label(node)} is reached from two instances; drawn in the first (${why})`);
            return;
        }
        owner.set(node.id(), instId);
    };

    // 1. GitLab nodes through the instance's own edges. (Graph node data carries the label, type,
    //    dimensions and tags, not model fields, so ownership is read from edges, never instance_name.)
    instances.forEach((i) => owner.set(i.id(), i.id()));
    [E.runsComponent, E.registersRunner, E.viaProvider, E.streams].forEach((type) =>
        _edges(cy, type).forEach((e) => claim(e.target(), owner.get(e.source().id()), type)));
    // A runner manager belongs to the instance of the registration it authenticates as.
    _edges(cy, E.asRunner).forEach((e) => claim(e.source(), owner.get(e.target().id()), E.asRunner));

    // 2. Foreign nodes through the edge that reaches them.
    const services = new Set();
    const managerServices = new Set();
    const dataKind = new Map();      // node id -> index in DATA_EDGES
    const outsideOf = new Map();     // node id -> source id
    const ingress = new Set();
    const jobPlatforms = new Set();
    _edges(cy, E.runsOn).forEach((e) => {
        claim(e.target(), owner.get(e.source().id()), E.runsOn);
        (e.source().data("entity_type") === T.manager ? managerServices : services).add(e.target().id());
    });
    DATA_EDGES.forEach((type, k) => _edges(cy, type).forEach((e) => {
        claim(e.target(), owner.get(e.source().id()), type);
        if (!dataKind.has(e.target().id())) dataKind.set(e.target().id(), k);
    }));
    _edges(cy, E.jobs).forEach((e) => { claim(e.target(), owner.get(e.source().id()), E.jobs); jobPlatforms.add(e.target().id()); });
    _edges(cy, E.routes).forEach((e) => {
        const tgt = e.target();
        const instId = owner.get(tgt.id());
        if (!instId) return;
        claim(e.source(), instId, E.routes);
        ingress.add(e.source().id());
    });
    OUTSIDE_EDGES.forEach((type) => _edges(cy, type).forEach((e) => {
        const instId = owner.get(e.source().id());
        if (!instId || owner.has(e.target().id())) return;
        outsideOf.set(e.target().id(), instId);
    }));

    // 3. Bands per instance.
    const bands = new Map();
    const outside = new Map();
    instances.forEach((i) => {
        bands.set(i.id(), {ingress: [], compute: [], data: [], runners: [], identity: []});
        outside.set(i.id(), []);
    });
    const serviceTypes = new Set();
    const leftovers = [];
    cy.nodes().forEach((n) => {
        const id = n.id();
        const t = n.data("entity_type") || "";
        if (t === T.instance || n.data("_is_badge")) return;
        if (outsideOf.has(id)) { outside.get(outsideOf.get(id)).push(n); return; }
        const instId = owner.get(id);
        if (!instId) { leftovers.push(n); return; }
        const b = bands.get(instId);
        // A process that runs on a service is drawn inside that service's box, not in a band.
        if (PROCESS_TYPES.has(t) && _edges(cy, E.runsOn).some((e) => e.source().id() === id)) return;
        if (services.has(id) || managerServices.has(id)) serviceTypes.add(t);
        if (ingress.has(id)) b.ingress.push(n);
        else if (managerServices.has(id) || t === T.manager || jobPlatforms.has(id) || t === T.runner) b.runners.push(n);
        else if (services.has(id) || t === T.component || t === T.gitaly) b.compute.push(n);
        else if (dataKind.has(id)) b.data.push(n);
        else if (t === T.sso || t === T.audit) b.identity.push(n);
        else if (t.startsWith("gitlab__")) b.identity.push(n);
        else leftovers.push(n);
    });
    bands.forEach((b) => {
        b.compute.sort((a, c) => _computeRank(cy, a) - _computeRank(cy, c) || _label(a).localeCompare(_label(c)));
        b.data.sort((a, c) => dataKind.get(a.id()) - dataKind.get(c.id()) || _label(a).localeCompare(_label(c)));
        b.runners.sort((a, c) => _runnerRank(a, managerServices, jobPlatforms) - _runnerRank(c, managerServices, jobPlatforms)
            || _label(a).localeCompare(_label(c)));
        b.ingress.sort((a, c) => _label(a).localeCompare(_label(c)));
        b.identity.sort((a, c) => String(a.data("entity_type")).localeCompare(String(c.data("entity_type"))) || _label(a).localeCompare(_label(c)));
    });
    return {bands, outside, leftovers, serviceTypes};
}

function _computeRank(cy, node) {
    // A service box ranks by the first-ranked process inside it. Graph data carries no model fields,
    // so a component is ranked by the first component word its name contains ("staging · workhorse").
    const members = [node, ..._edges(cy, E.runsOn).filter((e) => e.target().id() === node.id()).map((e) => e.source())];
    return Math.min(...members.map((m) => {
        if (m.data("entity_type") === T.gitaly) return COMPONENT_ORDER.length;
        const name = _label(m).toLowerCase().replace(/[\s-]+/g, "_");
        const k = COMPONENT_ORDER.findIndex((c) => name.includes(c));
        return k < 0 ? COMPONENT_ORDER.length + 1 : k;
    }));
}

function _runnerRank(node, managerServices, jobPlatforms) {
    if (managerServices.has(node.id()) || node.data("entity_type") === T.manager) return 0;
    if (jobPlatforms.has(node.id())) return 1;
    return 2;
}

function _addDeploys(cy, plan) {
    plan.bands.forEach((b, instId) => {
        [...b.ingress, ...b.compute, ...b.data, ...b.runners, ...b.identity].forEach((n) => {
            cy.add({
                group: "edges",
                data: {id: `${SYN.deploys}:${instId}:${n.id()}`, source: instId, target: n.id(), edge_type: SYN.deploys},
                classes: SYN_CLASS,
            });
        });
    });
}

function _clear(cy) {
    cy.remove(cy.elements("." + SYN_CLASS));
}

// ---------------------------------------------------------------------------
// Placement
// ---------------------------------------------------------------------------

function _childrenOf(cy, parentId) {
    return cy.nodes().filter((n) => n.data("_viewport_parent") === parentId);
}

function _moveTree(cy, node, dx, dy) {
    if (!dx && !dy) return;
    const p = node.position();
    node.position({x: p.x + dx, y: p.y + dy});
    _childrenOf(cy, node.id()).forEach((c) => _moveTree(cy, c, dx, dy));
}

function _moveTreeTo(cy, node, x, y) {
    const p = node.position();
    _moveTree(cy, node, x - p.x, y - p.y);
}

//: Stack `nodes` top-down from (left, top); returns the column's width and bottom.
function _stack(cy, nodes, left, top) {
    let y = top;
    let width = 0;
    nodes.forEach((n) => {
        _moveTreeTo(cy, n, left + n.width() / 2, y + n.height() / 2);
        y += n.height() + GEOM.rowGap;
        width = Math.max(width, n.width());
    });
    return {width, bottom: nodes.length ? y - GEOM.rowGap : top};
}

//: Lay `nodes` left-to-right from (left, top); returns the row's right edge and bottom.
function _row(cy, nodes, left, top) {
    let x = left;
    let bottom = top;
    nodes.forEach((n) => {
        _moveTreeTo(cy, n, x + n.width() / 2, top + n.height() / 2);
        x += n.width() + GEOM.colGap / 2;
        bottom = Math.max(bottom, top + n.height());
    });
    return {right: nodes.length ? x - GEOM.colGap / 2 : left, bottom};
}

function _bandLabel(cy, instId, key, text, x, y) {
    cy.add({
        group: "nodes",
        data: {
            id: `${SYN.label}:${instId}:${key}`, label: text, entity_type: SYN.label,
            fill_color: "#FFFFFF", border_color: "#FFFFFF", label_color: "#6B7280",
        },
        classes: `${SYN_CLASS} gitlab-band-label`,
        position: {x: x + 60, y: y + GEOM.bandLabelHeight / 2 - 4},
        locked: true,
        grabbable: false,
        selectable: false,
    });
}

function _placeInstance(cy, inst, bands, x0, y0, inset) {
    const pad = _instancePadding(inset);
    const left = x0 + pad.left;
    const top = y0 + pad.top;
    const instId = inst.id();
    let x = left;
    let bottom = top;

    const column = (key, text, nodes) => {
        if (!nodes.length) return;
        if (text) _bandLabel(cy, instId, key, text, x, top);
        const col = _stack(cy, nodes, x, top + GEOM.bandLabelHeight);
        bottom = Math.max(bottom, col.bottom);
        x += Math.max(col.width, 120) + GEOM.colGap;
    };

    column("ingress", "Ingress", bands.ingress);

    // Compute, with the runners band under it.
    if (bands.compute.length || bands.runners.length) {
        const computeLeft = x;
        let width = 0;
        let y = top;
        if (bands.compute.length) {
            _bandLabel(cy, instId, "compute", "Compute", computeLeft, y);
            const col = _stack(cy, bands.compute, computeLeft, y + GEOM.bandLabelHeight);
            width = Math.max(width, col.width);
            y = col.bottom + GEOM.rowGap * 2;
        }
        if (bands.runners.length) {
            _bandLabel(cy, instId, "runners", "Runners", computeLeft, y);
            const row = _row(cy, bands.runners, computeLeft, y + GEOM.bandLabelHeight);
            width = Math.max(width, row.right - computeLeft);
            y = row.bottom;
        }
        bottom = Math.max(bottom, y);
        x += width + GEOM.colGap;
    }

    // Data stores wrap into further columns past GEOM.dataWrap rows.
    for (let k = 0; k < bands.data.length; k += GEOM.dataWrap) {
        column(`data-${k}`, k === 0 ? "Data stores" : "", bands.data.slice(k, k + GEOM.dataWrap));
    }
    column("identity", "Sign-in & audit", bands.identity);

    const width = Math.max(GEOM.instanceFloor.width, x - GEOM.colGap - x0 + pad.right);
    const height = Math.max(GEOM.instanceFloor.height, bottom - y0 + pad.bottom);
    inst.style({width, height});
    inst.position({x: x0 + width / 2, y: y0 + height / 2});
    inst.addClass("tap-viewport-parent");
    return {width, height};
}

function _placeOutside(cy, inst, nodes, right) {
    if (!nodes.length) return;
    const top = inst.position().y - inst.height() / 2 + GEOM.bandLabelHeight * 2;
    _stack(cy, nodes, right + GEOM.outsideGap, top);
}

function _placeLeftovers(cy, nodes, warn) {
    if (!nodes.length) return;
    const bb = cy.nodes().not(nodes).boundingBox();
    let x = bb.x1;
    const top = bb.y2 + GEOM.instanceGap / 2;
    nodes
        .sort((a, b) => _label(a).localeCompare(_label(b)))
        .forEach((n) => {
            warn("gitlab_unplaced", `${_label(n)} (${n.data("entity_type")}) is not reached from any GitLab instance's deployment; drawn under the picture`);
            _moveTreeTo(cy, n, x + n.width() / 2, top + n.height() / 2);
            x += n.width() + GEOM.colGap / 2;
        });
}

// ---------------------------------------------------------------------------
// Helpers and style
// ---------------------------------------------------------------------------

function _edges(cy, type) {
    return cy.edges().filter((e) => (e.data("edge_type") || e.data("label")) === type).toArray();
}

function _label(n) {
    return String(n.data("label") || n.data("name") || n.id());
}

function _style(cy) {
    cy.style()
        .selector(`node[entity_type = "${T.instance}"]`)
        .style({
            "shape": "round-rectangle",
            "background-color": "#FFF7F3",
            "background-opacity": 1,
            "border-width": 2,
            "border-color": "#E24329",
            "color": "#7A2A00",
        })
        .selector(".gitlab-band-label")
        .style({
            "shape": "rectangle",
            "background-opacity": 0,
            "border-width": 0,
            "width": 120,
            "height": 18,
            "label": "data(label)",
            "font-size": "12px",
            "font-weight": "600",
            "color": "#6B7280",
            "text-transform": "uppercase",
            "text-valign": "center",
            "text-halign": "center",
            "background-image": "none",
            "events": "no",
            "z-index": 20,
        })
        // The instance box already says which instance runs a process; the line would repeat it.
        .selector(`edge[edge_type = "${E.runsComponent}"]`)
        .style({"display": "none"})
        .update();
}
