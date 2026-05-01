using System.Text.Json;
using comp1110_backend.Model;
using Microsoft.Extensions.Caching.Memory;
using Model;

namespace comp1110_backend;

internal class View // json etc
{
    private readonly Controller controller;

    public View(IMemoryCache cache)
    {
        controller = new Controller(cache);
    }

    public void LoadInitialNetwork(TransportNetwork network)
    {
        controller.CurrentNetwork = network;
    }

    private async Task WriteBody(HttpContext context, String mimeType, String body)
    {
        context.Response.ContentType = mimeType;
        await using StreamWriter writer = new StreamWriter(context.Response.Body);
        await writer.WriteAsync(body);
    }
    
    public static string Debug()
    {
        return "Status Online: Ok";
    }

    private static string BuildSegmentKey(Segment segment)
    {
        string fromStop = segment.FromStop.StopName.Trim().ToLowerInvariant();
        string toStop = segment.ToStop.StopName.Trim().ToLowerInvariant();
        string firstStop = string.CompareOrdinal(fromStop, toStop) <= 0 ? fromStop : toStop;
        string secondStop = string.CompareOrdinal(fromStop, toStop) <= 0 ? toStop : fromStop;
        return $"{firstStop}<>{secondStop}:{segment.SegmentTransportationType}:{segment.Line}:{segment.FareDollars}:{segment.TimeMin}:{segment.ScenicIndex}";
    }

    private static string BuildRouteKey(IEnumerable<Segment> routeSegments)
    {
        return string.Join("|", routeSegments.Select(BuildSegmentKey));
    }

    public async Task GetRoute(HttpContext context)
    {
        string? startStop = context.Request.Query["start"];
        string? endStop = context.Request.Query["end"];

        if (startStop == null || endStop == null)
        {
            context.Response.StatusCode = StatusCodes.Status400BadRequest;
            return;
        }

        Console.WriteLine("Finding path for:  " + startStop + " to " + endStop);

        var possibleRoutes = controller.GetRoute(startStop, endStop);
        
        // remove duplicate routes:
        HashSet<string> seenRoutePaths = [];
        possibleRoutes?.Routes.RemoveAll(route => !seenRoutePaths.Add(BuildRouteKey(route.Segments)));
        
        var serialisedRouteString = JsonSerializer.Serialize(possibleRoutes);

        Console.WriteLine("Path found for: " + startStop + " to " + endStop);
        await WriteBody(context, "application/json", serialisedRouteString);
    }

    public async Task GetNetwork(HttpContext context)
    {
        var network = controller.CurrentNetwork;

        string serialisedBody = network.GetSerializedString();
       
        await WriteBody(context, "application/json", serialisedBody);
    }

    public async Task SetNetwork(HttpContext context)
    {
        try
        {
            var reader = new StreamReader(context.Request.Body);
            var networkString = await reader.ReadToEndAsync();
            reader.Close();

            var network = ModelUtility.DeserializeTransportNetwork(networkString);

            if (network == null)
            {
                context.Response.StatusCode = StatusCodes.Status422UnprocessableEntity;
                return;
            }

            await File.WriteAllTextAsync(Config.NetworkFilePath, networkString);

            controller.CurrentNetwork = network;
        
            context.Response.StatusCode = StatusCodes.Status200OK;
        }
        catch (Exception e)
        {
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            Console.WriteLine(e);
        }
    }
}
