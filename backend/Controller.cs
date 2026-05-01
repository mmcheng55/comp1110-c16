using comp1110_backend.Model;
using comp1110_backend.Model.Responses;
using comp1110_backend.Services;
using Microsoft.Extensions.Caching.Memory;
using Model;

namespace comp1110_backend;

internal class Controller
{
    private TransportNetwork currentNetwork = new ([], []);
    private readonly PathFindingService service = new();
    private readonly IMemoryCache routeCache;
    private int networkVersion = 0;

    public Controller(IMemoryCache cache)
    {
        routeCache = cache;
    }

    public TransportNetwork CurrentNetwork
    {
        get => currentNetwork;
        set
        {
            // Loads the graph before switching the current network.
            service.LoadNetwork(value);
            currentNetwork = value;
            Interlocked.Increment(ref networkVersion);
        }
    }

    // Finds a stop by its name in the currently loaded network.
    private Stop? lookUpStop(string stopName)
    {
        foreach (var stop in currentNetwork.AllStops)
        {
            if (stop.StopName == stopName)
            {
                return stop;
            }
        }

        return null;
    }

    // Resolves a route between two stop names using the selected strategy.
    public PossibleRoutes? GetRoute(string start, string end)
    {
        string cacheKey = $"route_{networkVersion}_{start}_{end}";
        if (routeCache.TryGetValue(cacheKey, out PossibleRoutes? cachedRoute))
        {
            return cachedRoute;
        }

        Stop? startStop = lookUpStop(start);
        Stop? endStop = lookUpStop(end);

        if (startStop == null || endStop == null)
        {
            return null;
        }
        
        var route = service.FindRoute(startStop, endStop, PathFindStrategyEnum.Dijkstra);
        routeCache.Set(cacheKey, route, TimeSpan.FromMinutes(30));
        return route;
    }
}