import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  User,
  Users,
  Camera,
  HeartHandshake,
  FileText,
  ExternalLink,
  GitBranch,
  ArrowLeft,
  ShieldCheck,
  X,
  BookOpen,
  Clock
} from 'lucide-react';
import CitationModal from './CitationModal';
import NarrativeBioGenerator from './NarrativeBioGenerator';
import GenerationalTreeView from './GenerationalTreeView';
import { fetchCachedJson } from '../utils/apiCache';

export default function PersonProfileView({ personId, onClose, onSelectPerson }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [isCitationOpen, setIsCitationOpen] = useState(false);
  const [photoError, setPhotoError] = useState(false);
  const [graphData, setGraphData] = useState(null);

  useEffect(() => {
    if (!personId) return;
    setLoading(true);
    setPhotoError(false);
    const cleanId = String(personId).replace('.json', '');
    fetchCachedJson(`/api/person/${cleanId}`)
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(() => {
        fetchCachedJson(`/api/person/${cleanId}.json`)
          .then(data => {
            setProfile(data);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });

    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [personId]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (lightboxPhoto) {
          setLightboxPhoto(null);
        } else if (onClose) {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxPhoto, onClose]);

  useEffect(() => {
    if (profile && !graphData) {
      fetchCachedJson('/api/graph.json')
        .then(data => {
          if (data && data.nodes) setGraphData(data);
        })
        .catch(console.error);
    }
  }, [profile, graphData]);

  if (!personId) return null;

  const primaryPhoto = profile?.photos?.[0];
  const parents = profile?.relationships?.filter(r => r.role === 'parent' || r.relationship_type === 'parent' || r.relationship_type === 'child_of') || [];
  const spouses = profile?.relationships?.filter(r => r.role === 'spouse' || r.relationship_type === 'spouse' || r.relationship_type === 'spouse_of') || [];
  const children = profile?.relationships?.filter(r => r.role === 'child' || r.relationship_type === 'child' || r.relationship_type === 'parent_of') || [];

  const person = profile?.person || {};
  const facts = profile?.facts || [];
  const photos = profile?.photos || [];
  const obituaries = profile?.obituaries || [];
  const auditFlags = profile?.audit_flags || [];

  // Identify Burial and Marriage facts
  const burialFact = facts.find(
    f => f.fact_type === 'Burial' && (f.date_string || f.place_string)
  );
  const marriageFact = facts.find(
    f => f.fact_type === 'Marriage' && (f.date_string || f.place_string)
  );

  // Also-known-as calculation
  const composedDisplayName = `${person.first_name || person.name || ''} ${person.married_last_name || person.last_name || ''}`.trim();
  const akaParts = [];
  if (person.maiden_name && person.maiden_name.trim()) {
    const mn = person.maiden_name.trim();
    const mln = (person.married_last_name || person.last_name || '').trim();
    if (mn.toLowerCase() !== mln.toLowerCase()) {
      akaParts.push(`née ${mn}`);
    } else {
      akaParts.push(mn);
    }
  }
  if (
    person.name &&
    person.name.trim() &&
    person.name.trim().toLowerCase() !== composedDisplayName.toLowerCase() &&
    !akaParts.some(p => p.toLowerCase().includes(person.name.trim().toLowerCase()))
  ) {
    akaParts.push(person.name.trim());
  }
  const akaLine = akaParts.join(' • ');

  // Build timeline events from facts with a 4-digit year + dated photos
  const timelineEvents = [];
  const majorFactTypes = new Set(['Birth', 'Marriage', 'Death', 'Burial']);
  const seenFactEvents = new Set();

  facts.forEach(fact => {
    const yearMatch = fact.date_string?.match(/\b(\d{4})\b/);
    if (!yearMatch) return;
    const year = yearMatch[1];
    const type = fact.fact_type || 'Event';
    const dedupeKey = `${type}|${fact.date_string || ''}|${fact.place_string || ''}`;
    if (seenFactEvents.has(dedupeKey)) return;
    seenFactEvents.add(dedupeKey);

    timelineEvents.push({
      type,
      year,
      date: fact.date_string,
      place: fact.place_string,
      description: (!fact.place_string && fact.value_string && fact.value_string !== fact.date_string) ? fact.value_string : null,
      isMajor: majorFactTypes.has(type)
    });
  });

  // Fallback for person-level birth/death if no matching fact had a 4-digit year
  const hasBirthFactEvent = timelineEvents.some(e => e.type === 'Birth');
  if (!hasBirthFactEvent && (person.birth_date || person.birth_place)) {
    const birthYear = person.birth_date?.match(/\b(\d{4})\b/)?.[1];
    if (birthYear) {
      timelineEvents.push({
        type: 'Birth',
        year: birthYear,
        date: person.birth_date,
        place: person.birth_place,
        isMajor: true
      });
    }
  }

  const hasDeathFactEvent = timelineEvents.some(e => e.type === 'Death');
  if (!hasDeathFactEvent && (person.death_date || person.death_place)) {
    const deathYear = person.death_date?.match(/\b(\d{4})\b/)?.[1];
    if (deathYear) {
      timelineEvents.push({
        type: 'Death',
        year: deathYear,
        date: person.death_date,
        place: person.death_place,
        isMajor: true
      });
    }
  }

  // Photos with a parseable 4-digit date stay as media entries
  photos.forEach(photo => {
    const rawDate = photo.date_text || photo.approximate_year || '';
    const yearMatch = String(rawDate).match(/\b(\d{4})\b/);
    if (!yearMatch) return;
    timelineEvents.push({
      type: 'Media',
      year: yearMatch[1],
      date: String(rawDate),
      description: photo.subject_names || photo.title_or_caption,
      photo,
      isMajor: false
    });
  });

  // Sort by year, Birth first, Death last on ties (keep existing tie rules)
  timelineEvents.sort((a, b) => {
    const yearA = parseInt(a.year, 10) || 0;
    const yearB = parseInt(b.year, 10) || 0;
    if (a.type === 'Birth' && b.type !== 'Birth') return -1;
    if (b.type === 'Birth' && a.type !== 'Birth') return 1;
    if (a.type === 'Death' && b.type !== 'Death') return 1;
    if (b.type === 'Death' && a.type !== 'Death') return -1;
    return yearA - yearB;
  });

  // Section visibility rules
  const hasFamily = parents.length > 0 || spouses.length > 0 || children.length > 0;
  const hasTimeline = timelineEvents.length > 0;
  const hasStory = Boolean(profile?.person);
  const hasPhotos = photos.length > 0;
  const hasObituaries = obituaries.length > 0;
  const hasSources = facts.length > 0;
  const hasTree = Boolean(profile?.person);

  const navChips = [
    { id: 'profile-family', label: 'Family', visible: hasFamily },
    { id: 'profile-timeline', label: 'Timeline', visible: hasTimeline },
    { id: 'profile-story', label: 'Story', visible: hasStory },
    { id: 'profile-photos', label: 'Photos', visible: hasPhotos },
    { id: 'profile-obituary', label: 'Obituary', visible: hasObituaries },
    { id: 'profile-sources', label: 'Sources', visible: hasSources },
    { id: 'profile-tree', label: 'Tree', visible: hasTree }
  ].filter(chip => chip.visible);

  const scrollToSection = (sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#0F141A] text-[#F3EBE3] overflow-y-auto custom-scrollbar animate-fade-in flex flex-col font-sans">
      {/* Sticky Top Bar */}
      <header className="sticky top-0 z-40 bg-[#0F141A]/95 backdrop-blur-md border-b border-[#2A3644]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-2.5 flex items-center justify-between gap-3">
            {onClose ? (
              <button
                onClick={onClose}
                className="flex items-center gap-1.5 min-h-[44px] text-sm text-[#C87D53] hover:text-[#D4A373] transition-colors shrink-0 cursor-pointer"
                aria-label="Back to tree or previous view"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Archive</span>
              </button>
            ) : <div />}

            {/* Desktop Anchor Chips */}
            {!loading && profile && navChips.length > 0 && (
              <nav
                aria-label="Profile section navigation"
                className="hidden md:flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1"
              >
                {navChips.map(chip => (
                  <button
                    key={chip.id}
                    type="button"
                    onClick={() => scrollToSection(chip.id)}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-[#171E27] border border-[#2A3644] text-[#9EA9B6] hover:text-[#D4A373] hover:border-[#C87D53] transition-colors whitespace-nowrap cursor-pointer"
                  >
                    {chip.label}
                  </button>
                ))}
              </nav>
            )}

            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              <button
                onClick={() => setIsCitationOpen(true)}
                className="flex items-center gap-1.5 min-h-[44px] px-3 py-1 text-xs rounded-xl bg-[#171E27] border border-[#2A3644] text-[#C87D53] hover:text-[#D4A373] hover:border-[#C87D53] transition-colors cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Cite & Export</span>
              </button>
              {onClose && (
                <button
                  onClick={onClose}
                  className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-[#9EA9B6] hover:text-[#F3EBE3] transition-colors cursor-pointer"
                  aria-label="Close profile"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>

          {/* Mobile Anchor Chips Row */}
          {!loading && profile && navChips.length > 0 && (
            <nav
              aria-label="Profile section navigation mobile"
              className="flex md:hidden items-center gap-1.5 overflow-x-auto no-scrollbar pb-2.5 pt-0.5"
            >
              {navChips.map(chip => (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => scrollToSection(chip.id)}
                  className="px-3 py-1 rounded-full text-xs font-medium bg-[#171E27] border border-[#2A3644] text-[#9EA9B6] hover:text-[#D4A373] hover:border-[#C87D53] transition-colors whitespace-nowrap cursor-pointer shrink-0"
                >
                  {chip.label}
                </button>
              ))}
            </nav>
          )}
        </div>
      </header>

      {/* Main Single-Scroll Content */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6 sm:space-y-8">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 border-2 border-[#C87D53] border-t-transparent rounded-full animate-spin" />
            <span className="text-xs uppercase tracking-wider text-[#9EA9B6] font-mono">Loading dossier…</span>
          </div>
        ) : profile ? (
          <>
            {/* 1. Identity Card */}
            <section
              aria-label="Ancestor Identity"
              className="bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-8 shadow-xl"
            >
              <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start text-center sm:text-left">
                {/* Portrait in copper-bordered frame */}
                <div className="shrink-0 relative">
                  {primaryPhoto && !photoError ? (
                    <img
                      src={primaryPhoto.local_image_path.startsWith('/') ? primaryPhoto.local_image_path : '/' + primaryPhoto.local_image_path}
                      alt={`Portrait of ${person.first_name || person.name || ''} ${person.married_last_name || person.last_name || ''}`.trim() || 'Profile portrait'}
                      style={{
                        objectPosition: primaryPhoto.face_x ? `${primaryPhoto.face_x * 100}% ${primaryPhoto.face_y * 100}%` : '50% 22%'
                      }}
                      onError={() => setPhotoError(true)}
                      onClick={() => setLightboxPhoto(primaryPhoto)}
                      className="w-32 h-32 sm:w-44 sm:h-44 rounded-2xl object-cover border-2 border-[#C87D53]/40 shadow-lg cursor-pointer hover:border-[#C87D53] transition-colors"
                    />
                  ) : (
                    <div className="w-32 h-32 sm:w-44 sm:h-44 rounded-2xl bg-[#0F141A] border-2 border-[#C87D53]/40 flex items-center justify-center shadow-lg">
                      <User className="w-14 h-14 sm:w-16 sm:h-16 text-[#C87D53]/70" />
                    </div>
                  )}
                </div>

                {/* Identity Details */}
                <div className="flex-1 min-w-0 w-full">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-2">
                    {person.evidence_level === 4 && (
                      <span className="px-2.5 py-0.5 rounded-full bg-purple-950/60 text-purple-200 text-xs flex items-center gap-1 border border-purple-700/50">
                        <ShieldCheck className="w-3 h-3 text-[#C87D53]" /> DNA Verified
                      </span>
                    )}
                    {person.evidence_level === 3 && (
                      <span className="px-2.5 py-0.5 rounded-full bg-emerald-950/60 text-emerald-200 text-xs flex items-center gap-1 border border-emerald-700/50">
                        <ShieldCheck className="w-3 h-3 text-[#C87D53]" /> Primary Source
                      </span>
                    )}
                    {person.evidence_level === 2 && (
                      <span className="px-2.5 py-0.5 rounded-full bg-amber-950/60 text-amber-200 text-xs flex items-center gap-1 border border-amber-700/50">
                        <ShieldCheck className="w-3 h-3 text-[#C87D53]" /> Indexed
                      </span>
                    )}
                    <span className="px-2.5 py-0.5 rounded-full bg-[#0F141A] text-[#9EA9B6] text-xs border border-[#2A3644] font-mono">
                      #{person.person_id}
                    </span>
                  </div>

                  <h1 className="font-serif-header text-2xl sm:text-4xl lg:text-5xl text-[#F3EBE3] tracking-tight font-medium break-words">
                    {person.first_name || person.name}{' '}
                    <span className="font-bold">{person.married_last_name || person.last_name}</span>
                  </h1>

                  {akaLine && (
                    <p className="mt-1.5 text-sm text-[#9EA9B6] italic font-editorial-body">
                      Also known as: <span className="text-[#F3EBE3] not-italic">{akaLine}</span>
                    </p>
                  )}

                  {/* Labeled Vitals Rows */}
                  {(person.birth_date || person.birth_place || person.death_date || person.death_place || burialFact) && (
                    <div className="mt-5 pt-4 border-t border-[#2A3644] grid grid-cols-1 gap-2.5 text-xs sm:text-sm">
                      {(person.birth_date || person.birth_place) && (
                        <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                          <span className="uppercase tracking-wider text-[#9EA9B6] font-bold text-[11px] sm:w-20 shrink-0">
                            BORN
                          </span>
                          <div className="text-[#F3EBE3]">
                            {person.birth_date && <span className="font-medium">{person.birth_date}</span>}
                            {person.birth_date && person.birth_place && <span className="text-[#9EA9B6] mx-2">•</span>}
                            {person.birth_place && <span className="text-[#9EA9B6]">{person.birth_place}</span>}
                          </div>
                        </div>
                      )}

                      {(person.death_date || person.death_place) && (
                        <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                          <span className="uppercase tracking-wider text-[#9EA9B6] font-bold text-[11px] sm:w-20 shrink-0">
                            DIED
                          </span>
                          <div className="text-[#F3EBE3]">
                            {person.death_date && <span className="font-medium">{person.death_date}</span>}
                            {person.death_date && person.death_place && <span className="text-[#9EA9B6] mx-2">•</span>}
                            {person.death_place && <span className="text-[#9EA9B6]">{person.death_place}</span>}
                          </div>
                        </div>
                      )}

                      {burialFact && (
                        <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                          <span className="uppercase tracking-wider text-[#9EA9B6] font-bold text-[11px] sm:w-20 shrink-0">
                            BURIED
                          </span>
                          <div className="text-[#F3EBE3]">
                            {burialFact.date_string && <span className="font-medium">{burialFact.date_string}</span>}
                            {burialFact.date_string && burialFact.place_string && <span className="text-[#9EA9B6] mx-2">•</span>}
                            {burialFact.place_string && <span className="text-[#9EA9B6]">{burialFact.place_string}</span>}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/* Audit Quality-Flags Card (directly below Identity when non-empty) */}
            {auditFlags.length > 0 && (
              <section
                aria-label="Archival Quality Flags"
                className="bg-[#171E27] border border-amber-700/40 rounded-2xl p-4 sm:p-5 shadow-md"
              >
                <h2 className="font-serif-header text-sm font-bold text-amber-300 mb-2.5 flex items-center gap-2 uppercase tracking-wider">
                  <ShieldCheck className="w-4 h-4 text-[#C87D53]" />
                  Quality Flags
                </h2>
                <div className="space-y-2">
                  {auditFlags.map((flag, idx) => (
                    <p key={idx} className="text-xs text-[#F3EBE3] leading-relaxed">
                      <strong className="text-amber-300 uppercase tracking-wider text-[11px] mr-1.5">
                        {flag.category || flag.flag || 'Notice'}:
                      </strong>
                      <span className="text-[#9EA9B6]">{flag.description || flag.detail}</span>
                    </p>
                  ))}
                </div>
              </section>
            )}

            {/* 2. Family Card */}
            {hasFamily && (
              <section
                id="profile-family"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-6 shadow-md space-y-6"
              >
                <div className="border-b border-[#2A3644] pb-3 flex items-center gap-2.5">
                  <Users className="w-5 h-5 text-[#C87D53]" />
                  <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold">
                    Family & Immediate Kin
                  </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Parents Group */}
                  {parents.length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[#9EA9B6] mb-3">
                        Parents
                      </h3>
                      <div className="space-y-2">
                        {parents.map((rel, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)}
                            disabled={!rel.rel_id}
                            className={`w-full flex items-center justify-between gap-3 p-3 rounded-xl bg-[#0F141A] border border-[#2A3644] text-left transition-colors ${
                              rel.rel_id
                                ? 'hover:border-[#C87D53] cursor-pointer group'
                                : 'cursor-default opacity-75'
                            }`}
                            title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-8 h-8 rounded-full bg-[#171E27] border border-[#2A3644] flex items-center justify-center text-[#C87D53] shrink-0">
                                <User className="w-4 h-4" />
                              </div>
                              <span
                                className={`text-sm font-semibold truncate ${
                                  rel.rel_id
                                    ? 'text-[#C87D53] group-hover:text-[#D4A373] group-hover:underline'
                                    : 'text-[#F3EBE3]'
                                }`}
                              >
                                {rel.rel_name}
                              </span>
                            </div>
                            {rel.rel_id && (
                              <span className="text-xs font-mono text-[#9EA9B6] group-hover:text-[#D4A373] shrink-0">
                                #{rel.rel_id} →
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Spouse Group */}
                  {spouses.length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[#9EA9B6] mb-3">
                        Spouse
                      </h3>
                      <div className="space-y-2">
                        {spouses.map((rel, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)}
                            disabled={!rel.rel_id}
                            className={`w-full flex items-center justify-between gap-3 p-3 rounded-xl bg-[#0F141A] border border-[#2A3644] text-left transition-colors ${
                              rel.rel_id
                                ? 'hover:border-[#C87D53] cursor-pointer group'
                                : 'cursor-default opacity-75'
                            }`}
                            title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-8 h-8 rounded-full bg-[#171E27] border border-[#2A3644] flex items-center justify-center text-[#C87D53] shrink-0">
                                <User className="w-4 h-4" />
                              </div>
                              <span
                                className={`text-sm font-semibold truncate ${
                                  rel.rel_id
                                    ? 'text-[#C87D53] group-hover:text-[#D4A373] group-hover:underline'
                                    : 'text-[#F3EBE3]'
                                }`}
                              >
                                {rel.rel_name}
                              </span>
                            </div>
                            {rel.rel_id && (
                              <span className="text-xs font-mono text-[#9EA9B6] group-hover:text-[#D4A373] shrink-0">
                                #{rel.rel_id} →
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                      {marriageFact && (
                        <div className="mt-2.5 px-3 py-2 rounded-xl bg-[#0F141A]/70 border border-[#2A3644] text-xs flex flex-wrap items-baseline gap-x-2">
                          <span className="uppercase tracking-wider text-[#9EA9B6] font-bold text-[10px]">
                            MARRIAGE
                          </span>
                          {marriageFact.date_string && (
                            <span className="text-[#F3EBE3] font-medium">{marriageFact.date_string}</span>
                          )}
                          {marriageFact.date_string && marriageFact.place_string && (
                            <span className="text-[#9EA9B6]">•</span>
                          )}
                          {marriageFact.place_string && (
                            <span className="text-[#9EA9B6]">{marriageFact.place_string}</span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Children as a NUMBERED list of clickable names */}
                {children.length > 0 && (
                  <div className={parents.length > 0 || spouses.length > 0 ? 'pt-4 border-t border-[#2A3644]' : ''}>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#9EA9B6] mb-3">
                      Children ({children.length})
                    </h3>
                    <ol className="grid grid-cols-1 sm:grid-cols-2 gap-2 list-none">
                      {children.map((rel, i) => (
                        <li key={i}>
                          <button
                            type="button"
                            onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)}
                            disabled={!rel.rel_id}
                            className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl bg-[#0F141A] border border-[#2A3644] text-left transition-colors ${
                              rel.rel_id
                                ? 'hover:border-[#C87D53] cursor-pointer group'
                                : 'cursor-default opacity-75'
                            }`}
                            title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                          >
                            <div className="flex items-baseline gap-2.5 min-w-0">
                              <span className="text-xs font-mono font-bold text-[#9EA9B6] w-6 shrink-0">
                                {i + 1}.
                              </span>
                              <span
                                className={`text-sm font-semibold truncate ${
                                  rel.rel_id
                                    ? 'text-[#C87D53] group-hover:text-[#D4A373] group-hover:underline'
                                    : 'text-[#F3EBE3]'
                                }`}
                              >
                                {rel.rel_name}
                              </span>
                            </div>
                            {rel.rel_id && (
                              <span className="text-xs font-mono text-[#9EA9B6] group-hover:text-[#D4A373] shrink-0">
                                #{rel.rel_id} →
                              </span>
                            )}
                          </button>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </section>
            )}

            {/* 3. Timeline Card */}
            {hasTimeline && (
              <section
                id="profile-timeline"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-6 shadow-md"
              >
                <div className="border-b border-[#2A3644] pb-3 mb-5 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Clock className="w-5 h-5 text-[#C87D53]" />
                    <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold">
                      Chronological Timeline
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-[#9EA9B6] bg-[#0F141A] border border-[#2A3644] px-2.5 py-0.5 rounded-full">
                    {timelineEvents.length} {timelineEvents.length === 1 ? 'event' : 'events'}
                  </span>
                </div>

                <div className="relative border-l-2 border-[#2A3644] ml-3 sm:ml-4 space-y-6">
                  {timelineEvents.map((evt, idx) => (
                    <div key={idx} className="relative pl-6">
                      {evt.isMajor ? (
                        <div className="absolute -left-[9px] top-1 w-4 h-4 bg-[#0F141A] rounded-full border-2 border-[#C87D53]" />
                      ) : (
                        <div className="absolute -left-[5px] top-2 w-2 h-2 bg-[#9EA9B6] rounded-full" />
                      )}
                      <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-4">
                        <div className="w-14 shrink-0">
                          <span className="text-xs font-mono font-bold text-[#C87D53]">
                            {evt.year}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="font-semibold text-[#F3EBE3] text-sm block">
                            {evt.type}
                          </span>
                          {(evt.date || evt.place) && (
                            <p className="text-xs sm:text-sm text-[#9EA9B6] mt-0.5">
                              {evt.date}
                              {evt.date && evt.place && ' • '}
                              {evt.place && <span>{evt.place}</span>}
                            </p>
                          )}
                          {evt.description && (
                            <p className="text-xs sm:text-sm text-[#9EA9B6] mt-0.5">
                              {evt.description}
                            </p>
                          )}
                          {evt.photo && (
                            <img
                              src={evt.photo.local_image_path.startsWith('/') ? evt.photo.local_image_path : '/' + evt.photo.local_image_path}
                              alt={evt.description || 'Preserved timeline record'}
                              className="mt-2 w-16 h-16 object-cover rounded-lg border border-[#2A3644] hover:border-[#C87D53] cursor-pointer transition-colors"
                              onClick={() => setLightboxPhoto(evt.photo)}
                            />
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 4. Life Story Section */}
            {hasStory && (
              <section id="profile-story" className="scroll-mt-20">
                <NarrativeBioGenerator person={profile.person} onSelectPerson={onSelectPerson} />
              </section>
            )}

            {/* 5. Photos Section */}
            {hasPhotos && (
              <section
                id="profile-photos"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-6 shadow-md"
              >
                <div className="border-b border-[#2A3644] pb-3 mb-5 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Camera className="w-5 h-5 text-[#C87D53]" />
                    <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold">
                      Photographs & Archival Media
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-[#9EA9B6] bg-[#0F141A] border border-[#2A3644] px-2.5 py-0.5 rounded-full">
                    {photos.length}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {photos.map(photo => (
                    <div
                      key={photo.photo_id}
                      onClick={() => setLightboxPhoto(photo)}
                      className="group relative aspect-square bg-[#0F141A] border border-[#2A3644] hover:border-[#C87D53] rounded-xl overflow-hidden cursor-pointer shadow-sm transition-all"
                    >
                      <img
                        src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path}
                        alt={photo.subject_names || 'Preserved family photograph'}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 6. Obituary Section */}
            {hasObituaries && (
              <section
                id="profile-obituary"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-6 shadow-md space-y-4"
              >
                <div className="border-b border-[#2A3644] pb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <HeartHandshake className="w-5 h-5 text-[#C87D53]" />
                    <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold">
                      Preserved Obituary
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-[#9EA9B6] bg-[#0F141A] border border-[#2A3644] px-2.5 py-0.5 rounded-full">
                    {obituaries.length}
                  </span>
                </div>

                <div className="space-y-4">
                  {obituaries.map((obit, idx) => (
                    <div
                      key={obit.id || idx}
                      className="bg-[#0F141A] border border-[#2A3644] rounded-2xl p-5 sm:p-6 space-y-3"
                    >
                      {(obit.deceased_name || obit.cemetery_location) && (
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#2A3644] pb-2.5">
                          {obit.deceased_name && (
                            <h3 className="font-serif-header text-lg font-bold text-[#F3EBE3]">
                              {obit.deceased_name}
                            </h3>
                          )}
                          {obit.cemetery_location && (
                            <span className="text-xs text-[#9EA9B6] font-mono">
                              {obit.cemetery_location}
                            </span>
                          )}
                        </div>
                      )}
                      <div className="text-base leading-relaxed text-[#F3EBE3] font-editorial-body whitespace-pre-wrap">
                        {obit.full_text}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 7. Sources Section */}
            {hasSources && (
              <section
                id="profile-sources"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl overflow-hidden shadow-md"
              >
                <div className="p-5 sm:p-6 border-b border-[#2A3644] flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <FileText className="w-5 h-5 text-[#C87D53]" />
                    <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold">
                      Archive Sources & Documented Facts
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-[#9EA9B6] bg-[#0F141A] border border-[#2A3644] px-2.5 py-0.5 rounded-full">
                    {facts.length}
                  </span>
                </div>

                <div className="divide-y divide-[#2A3644]">
                  {facts.map((fact, idx) => (
                    <div key={idx} className="p-5 sm:p-6 hover:bg-[#0F141A]/40 transition-colors">
                      <div className="flex flex-wrap justify-between items-baseline gap-2 mb-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#9EA9B6]">
                          {fact.fact_type}
                        </span>
                        {(fact.date_string || fact.place_string) && (
                          <span className="text-xs text-[#9EA9B6] font-mono">
                            {fact.date_string}
                            {fact.date_string && fact.place_string && ' • '}
                            {fact.place_string}
                          </span>
                        )}
                      </div>
                      {fact.value_string && (
                        <p className="text-sm text-[#F3EBE3] mb-2.5">{fact.value_string}</p>
                      )}

                      {fact.citations && fact.citations.map((cit, cIdx) => {
                        const isHttpUrl =
                          typeof cit.source_url === 'string' &&
                          (cit.source_url.startsWith('http://') || cit.source_url.startsWith('https://')) &&
                          !cit.source_url.includes('lynncjackson');

                        return (
                          <div key={cIdx} className="mt-2.5 pl-3 border-l-2 border-[#2A3644]">
                            {isHttpUrl ? (
                              <a
                                href={cit.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-semibold text-[#C87D53] hover:text-[#D4A373] hover:underline inline-flex items-center gap-1 transition-colors"
                              >
                                {cit.source_title || 'Archival Document'}
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ) : (
                              <span className="text-xs font-semibold text-[#9EA9B6] inline-flex items-center gap-1">
                                {cit.source_title || 'Archival Document'}
                              </span>
                            )}
                            {cit.evidence_text && (
                              <p className="text-xs text-[#9EA9B6] mt-1 italic font-editorial-body">
                                "{cit.evidence_text}"
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 8. Tree Section */}
            {hasTree && (
              <section
                id="profile-tree"
                className="scroll-mt-20 bg-[#171E27] border border-[#2A3644] rounded-2xl p-5 sm:p-6 shadow-md space-y-4"
              >
                <div className="border-b border-[#2A3644] pb-3 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-serif-header text-xl sm:text-2xl text-[#F3EBE3] font-bold flex items-center gap-2.5">
                      <GitBranch className="w-5 h-5 text-[#C87D53]" />
                      {person.name} — Genetic Pedigree & Lineage Tree
                    </h2>
                    <p className="text-xs text-[#9EA9B6] mt-1">
                      Mathematical 2D generational layout with orthogonal bus-bar connectors. Select any related node to navigate.
                    </p>
                  </div>
                </div>

                <div className="w-full h-[480px] sm:h-[620px] rounded-2xl overflow-hidden border border-[#2A3644] bg-[#0F141A]">
                  <GenerationalTreeView
                    graphData={
                      graphData && graphData.nodes?.some(n => Number(n.id) === Number(person.person_id))
                        ? graphData
                        : {
                            nodes: [
                              {
                                id: person.person_id,
                                label: person.name,
                                birth_info: person.birth_info,
                                source_page: person.source_page
                              },
                              ...(profile.relationships || []).map(r => ({
                                id: r.rel_id,
                                label: r.rel_name,
                                birth_info: r.role
                              }))
                            ],
                            edges: (profile.relationships || []).map(r => ({
                              from: r.role === 'child' ? r.rel_id : person.person_id,
                              to: r.role === 'child' ? person.person_id : r.rel_id,
                              type: r.relationship_type
                            }))
                          }
                    }
                    onSelectNode={(p) => {
                      if (onSelectPerson && p.id !== person.person_id) {
                        onSelectPerson(p.id);
                      }
                    }}
                    focalId={person.person_id}
                  />
                </div>
              </section>
            )}
          </>
        ) : null}
      </main>

      {/* Lightbox Portal */}
      {lightboxPhoto && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-black/95 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 md:p-8"
          onClick={() => setLightboxPhoto(null)}
        >
          <button
            onClick={() => setLightboxPhoto(null)}
            className="absolute top-4 right-4 sm:top-6 sm:right-6 text-[#9EA9B6] hover:text-[#F3EBE3] bg-[#171E27] border border-[#2A3644] hover:border-[#C87D53] p-2.5 rounded-full transition-all z-[10000] min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer"
            aria-label="Close media preview"
          >
            <X className="w-5 h-5" />
          </button>
          <div
            className="relative max-w-6xl w-full max-h-[92vh] flex flex-col lg:flex-row bg-[#171E27] border border-[#2A3644] rounded-2xl overflow-hidden shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex-1 bg-[#0F141A] flex items-center justify-center p-2 sm:p-4 min-h-[30vh]">
              <img
                src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                alt={lightboxPhoto.subject_names || 'High-resolution archival record'}
                className="max-w-full max-h-[45vh] lg:max-h-[75vh] object-contain rounded-lg"
              />
            </div>
            <div className="w-full lg:w-96 bg-[#171E27] border-t lg:border-t-0 lg:border-l border-[#2A3644] p-5 sm:p-6 lg:p-8 flex flex-col overflow-y-auto text-[#F3EBE3]">
              <h3 className="font-serif-header text-xl sm:text-2xl mb-3 sm:mb-4 leading-tight text-[#F3EBE3]">
                {lightboxPhoto.subject_names || 'Archival Record'}
              </h3>
              <div className="space-y-3 sm:space-y-4 text-xs sm:text-sm">
                {(lightboxPhoto.date_text || lightboxPhoto.approximate_year) && (
                  <div>
                    <span className="text-[#9EA9B6] uppercase tracking-wider text-[11px] font-bold block mb-0.5">
                      Est. Date
                    </span>
                    {lightboxPhoto.date_text || lightboxPhoto.approximate_year}
                  </div>
                )}
                {(lightboxPhoto.description || lightboxPhoto.title_or_caption) && (
                  <div>
                    <span className="text-[#9EA9B6] uppercase tracking-wider text-[11px] font-bold block mb-0.5">
                      Description
                    </span>
                    {lightboxPhoto.description || lightboxPhoto.title_or_caption}
                  </div>
                )}
                {(lightboxPhoto.source_collection || lightboxPhoto.dataset_source) && (
                  <div>
                    <span className="text-[#9EA9B6] uppercase tracking-wider text-[11px] font-bold block mb-0.5">
                      Collection
                    </span>
                    {lightboxPhoto.source_collection || lightboxPhoto.dataset_source}
                  </div>
                )}
                {(() => {
                  const photoSourceUrl = lightboxPhoto.source_url || lightboxPhoto.original_source_url;
                  const isPhotoHttpUrl =
                    typeof photoSourceUrl === 'string' &&
                    (photoSourceUrl.startsWith('http://') || photoSourceUrl.startsWith('https://')) &&
                    !photoSourceUrl.includes('lynncjackson');

                  return isPhotoHttpUrl ? (
                    <div className="pt-4 sm:pt-6 mt-4 sm:mt-6 border-t border-[#2A3644]">
                      <a
                        href={photoSourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 font-bold text-[#C87D53] hover:text-[#D4A373] hover:underline transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" /> View Original Archival Source
                      </a>
                    </div>
                  ) : (
                    <div className="pt-4 sm:pt-6 mt-4 sm:mt-6 border-t border-[#2A3644]">
                      <span className="text-emerald-400 text-xs font-semibold uppercase tracking-wider block">
                        Preserved in Digital Archive
                      </span>
                      <span className="text-[#9EA9B6] text-xs mt-1 block">
                        Preserved offline in unified photo catalog.
                      </span>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Citation Modal */}
      <CitationModal isOpen={isCitationOpen} onClose={() => setIsCitationOpen(false)} data={profile} type="person" />
    </div>
  );
}
