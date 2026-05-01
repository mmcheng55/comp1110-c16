using comp1110_backend.Model;
using comp1110_backend.Model.Responses;
using Model;
using Route = comp1110_backend.Model.Responses.Route;

namespace comp1110_backend.Services {
    enum PathFindStrategyEnum
    {
        Recursive,
        Bfs,
        Dijkstra
    }
    
    class PathFindingService
    {

        private readonly Dictionary<Stop, List<Segment>> stopNetwork = new();
        private readonly Dictionary<Stop, int> stopToIndex = new();
        private List<(int nextStopIndex, Segment segment)>[] recursiveAdjacency = [];
        
        private static string CanonicalStopName(string stopName)
        {
            return string.Concat(stopName.Where(c => !char.IsWhiteSpace(c))).ToLowerInvariant();
        }

        private static string BuildPathSignature(List<Segment> path)
        {
            return string.Join("|", path.Select(s =>
                $"{CanonicalStopName(s.FromStop.StopName)}>{CanonicalStopName(s.ToStop.StopName)}:{s.SegmentTransportationType}:{s.Line}:{s.TimeMin}:{s.FareDollars}:{s.ScenicIndex}"));
        }

        private static string BuildUndirectedSegmentKey(Segment segment)
        {
            string stopA = CanonicalStopName(segment.FromStop.StopName);
            string stopB = CanonicalStopName(segment.ToStop.StopName);
            string left = string.CompareOrdinal(stopA, stopB) <= 0 ? stopA : stopB;
            string right = string.CompareOrdinal(stopA, stopB) <= 0 ? stopB : stopA;
            return $"{left}<>{right}:{segment.SegmentTransportationType}:{segment.Line}:{segment.TimeMin}:{segment.FareDollars}:{segment.ScenicIndex}";
        }

        private static double OverlapRatio(HashSet<string> candidateEdges, HashSet<string> selectedEdges)
        {
            if (candidateEdges.Count == 0 || selectedEdges.Count == 0) return 0.0;
            int intersectionCount = candidateEdges.Count(edge => selectedEdges.Contains(edge));
            int minSize = Math.Min(candidateEdges.Count, selectedEdges.Count);
            return minSize == 0 ? 0.0 : (double)intersectionCount / minSize;
        }

        private static List<List<Segment>> SelectDiverseRoutes(
            List<(List<Segment> path, double cost, HashSet<string> edgeSet)> candidates,
            int routeCount)
        {
            if (routeCount <= 0 || candidates.Count == 0) return [];

            List<(List<Segment> path, double cost, HashSet<string> edgeSet)> ordered = candidates
                .OrderBy(c => c.cost)
                .ToList();

            List<(List<Segment> path, double cost, HashSet<string> edgeSet)> selected = [ordered[0]];
            ordered.RemoveAt(0);

            while (selected.Count < routeCount && ordered.Count > 0)
            {
                int bestIndex = -1;
                double bestScore = double.MaxValue;

                for (int i = 0; i < ordered.Count; i++)
                {
                    var candidate = ordered[i];
                    double maxOverlap = selected.Max(s => OverlapRatio(candidate.edgeSet, s.edgeSet));
                    if (maxOverlap > Config.DijkstraMaxAllowedOverlapRatio) continue;

                    double score = candidate.cost + (maxOverlap * Config.DijkstraDiversityPenaltyWeight);
                    if (score < bestScore)
                    {
                        bestScore = score;
                        bestIndex = i;
                    }
                }

                if (bestIndex == -1)
                {
                    // If strict overlap filtering blocks all remaining candidates, fall back to cheapest.
                    selected.Add(ordered[0]);
                    ordered.RemoveAt(0);
                    continue;
                }

                selected.Add(ordered[bestIndex]);
                ordered.RemoveAt(bestIndex);
            }

            return selected.Select(s => s.path).ToList();
        }

        // Builds a stop-to-segments adjacency map for undirected traversal.
        public void LoadNetwork(TransportNetwork network)
        {
            stopNetwork.Clear();
            stopToIndex.Clear();
            HashSet<Segment> uniqueSegments = new();
            recursiveAdjacency = new List<(int nextStopIndex, Segment segment)>[network.AllStops.Length];

            for (int i = 0; i < network.AllStops.Length; i++)
            {
                var stop = network.AllStops[i];
                stopToIndex[stop] = i;
                recursiveAdjacency[i] = [];
            }

            foreach (var segment in network.AllSegments)
            {
                if (segment.FromStop == null || segment.ToStop == null)
                {
                    throw new InvalidOperationException("Segment has null stops; check JSON payloads for 'from'/'to' objects.");
                }

                if (!uniqueSegments.Add(segment)) continue; // Ignore duplicate segments

                var stop1 = segment.FromStop;
                var stop2 = segment.ToStop;
                if (CanonicalStopName(stop1.StopName) == CanonicalStopName(stop2.StopName))
                {
                    continue; // Ignore alias/self-loop edges like "Wan Chai" -> "Wanchai".
                }

                if (!stopToIndex.TryGetValue(stop1, out var stop1Index) || !stopToIndex.TryGetValue(stop2, out var stop2Index))
                {
                    continue;
                }

                if (!stopNetwork.TryGetValue(stop1, out var value1))
                {
                    value1 = [];
                    stopNetwork[stop1] = value1;
                }
                value1.Add(segment);

                if (!stopNetwork.TryGetValue(stop2, out var value2))
                {
                    value2 = [];
                    stopNetwork[stop2] = value2;
                }
                value2.Add(segment);

                // Precompute undirected edges for recursive DFS to avoid per-step stop resolution.
                recursiveAdjacency[stop1Index].Add((stop2Index, segment));
                recursiveAdjacency[stop2Index].Add((stop1Index, segment));
            }
        }

        // Depth-first search with backtracking; caps depth to avoid runaway recursion.
        /// <summary>
        /// This approach is utilizing recursive approach to find the answer.
        /// If the depth exceeds the maximum depth, an error is throw to stop the process.
        /// </summary>
        /// <param name="current"></param>
        /// <param name="endingPoint"></param>
        /// <param name="visitedStops"></param>
        /// <param name="path"></param>
        /// <param name="foundRoutes"></param>
        /// <param name="visitedDepth"></param>
        /// <returns>
        /// 
        /// </returns>
        private void VisitSegmentRecursive(
            int currentIndex,
            int endingPointIndex,
            bool[] visitedStops,
            Segment[] pathBuffer,
            int pathLength,
            List<List<Segment>> foundRoutes,
            int visitedDepth,
            int maxRouteCount
        )
        {
            if (foundRoutes.Count >= maxRouteCount) return;

            // Stop to prevent extremely deep recursion / stack overflow
            if (visitedDepth > Config.MaximumDepth) return;
            
            // Check if destination is reached
            if (currentIndex == endingPointIndex)
            {
                List<Segment> route = new(pathLength);
                for (int i = 0; i < pathLength; i++)
                {
                    route.Add(pathBuffer[i]);
                }
                foundRoutes.Add(route);
                return;
            }

            // Mark current stop as visited to avoid cycles
            visitedStops[currentIndex] = true;

            // Iterate over all connected segments
            foreach (var (nextStopIndex, segment) in recursiveAdjacency[currentIndex])
            {
                // Skip stops we've already visited on this path
                if (visitedStops[nextStopIndex]) continue;

                // Recursively visit the next stop
                pathBuffer[pathLength] = segment;
                VisitSegmentRecursive(
                    nextStopIndex,
                    endingPointIndex,
                    visitedStops,
                    pathBuffer,
                    pathLength + 1,
                    foundRoutes,
                    visitedDepth + 1,
                    maxRouteCount
                );
            }
            
            // Backtrack: unmark the current stop so it can be visited by other paths
            visitedStops[currentIndex] = false;
        }

        // Breadth-first exploration that tracks per-path visited stops.
        private List<List<Segment>> FindRoutesBFS(Stop startingPoint, Stop endingPoint)
        {
            List<List<Segment>> foundRoutes = [];
            Queue<(Stop current, List<Segment> path, int depth)> queue = new();
            Dictionary<Stop, int> dequeuedCount = new(); // Global bounds to prevent exponential path blowup
            HashSet<string> seenPathSignatures = []; // Prevents duplicate paths

            queue.Enqueue((startingPoint, [], 0));

            while (queue.Count > 0 && foundRoutes.Count < 5) // Cap to avoid endless searches
            {
                var (current, path, depth) = queue.Dequeue();

                if (current.Equals(endingPoint))
                {
                    string signature = string.Join("->", path.Select(s => s.GetHashCode()));

                    if (!seenPathSignatures.Contains(signature))
                    {
                        foundRoutes.Add(path);
                        seenPathSignatures.Add(signature);
                    }
                    continue;
                }

                if (depth >= Config.MaximumDepth) continue;

                // Allow exploring alternative paths, but stop expanding the exact same node endlessly
                dequeuedCount.TryGetValue(current, out int count);
                if (count > 5) continue;
                dequeuedCount[current] = count + 1;

                if (!stopNetwork.TryGetValue(current, out var outgoing)) continue;

                HashSet<Stop> pathStops = [startingPoint];
                foreach (var s in path)
                {
                    pathStops.Add(s.FromStop);
                    pathStops.Add(s.ToStop);
                }

                foreach (var segment in outgoing)
                {
                    var nextStop = segment.FromStop.Equals(current) ? segment.ToStop : segment.FromStop;

                    // Fast O(1) cycle check
                    if (pathStops.Contains(nextStop)) continue;

                    List<Segment> newPath = path.ToList();
                    newPath.Add(segment);

                    queue.Enqueue((nextStop, newPath, depth + 1));
                }
            }

            return foundRoutes;
        }
        
        // Priority-queue search that returns up to k unique paths.
        private List<List<Segment>> FindRoutesDijkstra(Stop startingPoint, Stop endingPoint, int kCount)
        {
            if (kCount <= 0) return [];

            int targetCandidateCount = Math.Max(kCount, kCount * Config.DijkstraCandidateMultiplier);
            List<(List<Segment> path, double cost, HashSet<string> edgeSet)> candidates = [];
            HashSet<string> seenPathSignatures = []; // Prevent duplicate full routes.
            Dictionary<(Stop stop, string? lastLine, string? lastType), int> dequeuedCount = new();
            Dictionary<Segment, int> segmentUsageCount = new();

            // Priority Queue: (CurrentStop, PathTaken), Priority: path cost
            PriorityQueue<(Stop current, List<Segment> path), double> pq = new();
            pq.Enqueue((startingPoint, []), 0);

            while (pq.Count > 0 && candidates.Count < targetCandidateCount)
            {
                if (!pq.TryDequeue(out var state, out double cost)) continue;
                var (current, path) = state;

                if (current.Equals(endingPoint))
                {
                    string signature = BuildPathSignature(path);

                    if (!seenPathSignatures.Contains(signature))
                    {
                        HashSet<string> edgeSet = path.Select(BuildUndirectedSegmentKey).ToHashSet();
                        candidates.Add((path, cost, edgeSet));
                        seenPathSignatures.Add(signature);
                        foreach (var usedSegment in path)
                        {
                            segmentUsageCount.TryGetValue(usedSegment, out var usageCountForSegment);
                            segmentUsageCount[usedSegment] = usageCountForSegment + 1;
                        }
                    }
                    continue;
                }

                // If we've already expanded this node for enough top routes, stop expanding it
                // Key by stop + incoming transit context to preserve more alternatives.
                string? incomingLine = path.Count > 0 ? path[^1].Line : null;
                string? incomingType = path.Count > 0 ? path[^1].SegmentTransportationType : null;
                var expansionKey = (current, incomingLine, incomingType);
                dequeuedCount.TryGetValue(expansionKey, out int count);
                if (count >= kCount * Config.DijkstraExpansionFactor) continue;
                dequeuedCount[expansionKey] = count + 1;

                if (!stopNetwork.TryGetValue(current, out var segments)) continue;

                foreach (var segment in segments)
                {
                    // Segments are undirected: move to the opposite end.
                    Stop nextStop = segment.FromStop.Equals(current) ? segment.ToStop : segment.FromStop;

                    // Anti-cycle checking without needing HashSet cloning
                    if (path.Any(s => s.FromStop.Equals(nextStop) || s.ToStop.Equals(nextStop))) continue;

                    // Calculate composite cost: minimise transfer, time, and cost
                    double timeCost = segment.TimeMin > 0 ? segment.TimeMin : 1.0;
                    double fareCost = segment.FareDollars > 0 ? segment.FareDollars : 0.0; // Re-enabled fare cost so cheaper modes like Tram become competitive
                    double transferPenalty = 1.0; // Base hop penalty
                    double scenicBonus = segment.ScenicIndex > 0 ? -segment.ScenicIndex * 0.5 : 0.0; // Bonus for scenic routes

                    // Check for transfer
                    if (path.Count > 0)
                    {
                        var lastSegment = path[^1];
                        if (lastSegment.SegmentTransportationType != segment.SegmentTransportationType || 
                            lastSegment.Line != segment.Line)
                        {
                            transferPenalty = 15.0; // Penalty weight for changing line/transport mode
                        }
                    }

                    // Promote route diversity: lightly penalize segments used by already-accepted routes.
                    segmentUsageCount.TryGetValue(segment, out int usageCount);
                    double diversityPenalty = usageCount * 6.0;

                    // Composite weight
                    double weight = timeCost + (fareCost * 2.0) + transferPenalty + scenicBonus + diversityPenalty;
                    double nextCost = cost + weight;

                    List<Segment> newPath = path.ToList();
                    newPath.Add(segment);
                    pq.Enqueue((nextStop, newPath), nextCost);
                }
            }

            return SelectDiverseRoutes(candidates, kCount);
        }        
        // Reconstructs a path from predecessor maps.
        private List<Segment> ReconstructPath(
            Stop end, 
            Dictionary<Stop, Stop?> prevStops, 
            Dictionary<Stop, Segment?> prevSegments)
        {
            List<Segment> path = [];
            Stop? current = end;
        
            while (current != null && prevSegments.TryGetValue(current, out var segment) && segment != null)
            {
                path.Insert(0, segment);
                current = prevStops[current];
            }
        
            return path;
        }

        // Normalizes segment orientation so each segment flows from the requested start.
        private static List<Segment> OrientPathFromStart(Stop start, List<Segment> path)
        {
            List<Segment> oriented = new(path.Count);
            Stop current = start;

            foreach (var segment in path)
            {
                if (segment.FromStop.Equals(current))
                {
                    oriented.Add(segment);
                    current = segment.ToStop;
                }
                else if (segment.ToStop.Equals(current))
                {
                    oriented.Add(new Segment(
                        segment.ToStop,
                        segment.FromStop,
                        segment.SegmentTransportationType,
                        segment.Line,
                        segment.FareDollars,
                        segment.TimeMin,
                        segment.ScenicIndex
                    ));
                    current = segment.FromStop;
                }
                else
                {
                    // Fallback for malformed paths: keep original segment if chain cannot be aligned.
                    oriented.Add(segment);
                }
            }

            return oriented;
        }

        // Entry point for route finding, dispatching by strategy.
        public PossibleRoutes FindRoute(
                Stop startingPoint, 
                Stop endingPoint, 
                PathFindStrategyEnum strategy
            )
        {
            if (CanonicalStopName(startingPoint.StopName) == CanonicalStopName(endingPoint.StopName))
            {
                return new PossibleRoutes([new Route([])]);
            }

            List<List<Segment>> foundRoutes = [];
        
            switch (strategy)
            {
                case PathFindStrategyEnum.Recursive:
                    if (!stopToIndex.TryGetValue(startingPoint, out var startingPointIndex) ||
                        !stopToIndex.TryGetValue(endingPoint, out var endingPointIndex))
                    {
                        break;
                    }

                    VisitSegmentRecursive(
                        startingPointIndex,
                        endingPointIndex,
                        new bool[recursiveAdjacency.Length],
                        new Segment[Math.Min(Config.MaximumDepth, recursiveAdjacency.Length)],
                        0,
                        foundRoutes,
                        0,
                        Config.MaximumRecursiveRoutes
                    );
                    break;
                case PathFindStrategyEnum.Bfs:
                    foundRoutes = FindRoutesBFS(startingPoint, endingPoint);
                    break;
                case PathFindStrategyEnum.Dijkstra:
                    foundRoutes = FindRoutesDijkstra(startingPoint, endingPoint, Config.DijkstraRouteCount);
                    break;
            }

            List<Route> routes = foundRoutes
                .Select(route => new Route(OrientPathFromStart(startingPoint, route)))
                .ToList();
            return new PossibleRoutes(routes);
        }
    }
}
