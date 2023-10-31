import sys, math, argparse
import numpy as np
import matplotlib.pyplot as plt
import datetime
from openpyxl import Workbook
import xlsxwriter
from planning import (
    rrt,
    rrt_star,
    rrt_gpu,
    rrt_star_gpu,
    EdgeCreator,
    DistanceComputator,
    StraightEdgeCreator,
    EuclideanDistanceComputator,
    EuclideanDistanceComputator_gpu,
    ObstacleCollisionChecker,
)
from edge import Edge
from obstacle import construct_circular_obstacles, WorldBoundary2D, RectangularObstacle, polyObstacle
from draw_cspace import draw

import random
from random import randrange
from scipy.spatial import ConvexHull, convex_hull_plot_2d
import pdb
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import itertools
from shapely.ops import unary_union
from numba import cuda



ALG_RRT = "rrt"
ALG_RRTstar = "rrt_star"
ALG_RRT_gpu = "rrt_gpu"
ALG_RRTstar_gpu = "rrt_star_gpu"

def euclidian_distance(a, b):
    return np.linalg.norm(a - b)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run sampling-based motion planning algorithm"
    )
    parser.add_argument(
        "--alg",
        choices=[ALG_RRT, ALG_RRTstar, ALG_RRT_gpu, ALG_RRTstar_gpu],
        required=False,
        default=ALG_RRTstar,
        dest="alg",
        help="algorithm, default to rrt",
    )
    parser.add_argument(
        "--env",
        choices=['simple', 'complex','complex_pro', 'blocked'],
        required=False,
        default='simple',
        dest="env",
        help="env, default to simple",
    )
    parser.add_argument(
        "--numIt",
        required=False,
        default=1000,
        type=int,
        dest="numIt",
        help="Number of iterations",
    )
    parser.add_argument(
        "--merge",
        required=False,
        action='store_true',
        dest="merge",
        help="Merge obstacles when generating environment",
    )
    parser.add_argument(
        "--seed",
        required=False,
        default=random.randint(0, 9999),
        type=int,
        dest="seed",
        help="Specify the range used to generate randoms seeds for obstalces",
    )
    parser.add_argument(
        "--save",
        choices=['dont', 'do'],
        required=False,
        default='dont',
        dest="save",
        help="save, save time data as a file",
    )
    parser.add_argument(
        "--exp",
        required=False,
        default=1,
        type=int,
        dest="exp",
        help="Specify the experiment number",
    )
    args = parser.parse_args(sys.argv[1:])
    return args


if __name__ == "__main__":
    rho_min = 0.5
    # cspace = [(-3, 3), (-1, 1), (-math.pi / 2, math.pi / 2)]
    # qI = (-2, -0.5, 0)
    # qG = (2, -0.5, math.pi / 2)
    # obstacles = construct_circular_obstacles(0.2)
    # obs_boundaries = [obstacle.get_boundaries() for obstacle in obstacles]
    
    args = parse_args()

    if args.env == 'simple':
        obs = [[(-0.25,0.25),(-3,1)],
                [(-0.25,0.25),(2,3)]]

        obstacles = []
        for ob in obs:
            obstacles.append(RectangularObstacle(ob[0],ob[1]))
        obs_boundaries = [obstacle.get_boundaries() for obstacle in obstacles]

    elif args.env == 'complex':
        obs = [[(-0.25,0.25),(-3,1)],
                [(-0.25,0.25),(2,3)],
                [(-5,-4),(-0.25,0.25)],
                [(-3,-0.25),(-0.25,0.25)],
                [(0.25,1),(-0.25,0.25)],
                [(2,5),(-0.25,0.25)],
                [(2.25,2.75),(-2,-0.25)]]

        obstacles = []
        for ob in obs:
            obstacles.append(RectangularObstacle(ob[0],ob[1]))
        obs_boundaries = [obstacle.get_boundaries() for obstacle in obstacles]
        
    elif args.env == 'blocked':
        obs = [[(-0.25,0.25),(-3,3)]]

        obstacles = []
        for ob in obs:
            obstacles.append(RectangularObstacle(ob[0],ob[1]))
        obs_boundaries = [obstacle.get_boundaries() for obstacle in obstacles]
        
    elif args.env == 'complex_pro':
        # obs = [[(-4.9,2.9),(-1,1),(0,-2),(4,1),(0,2)] ,
        #         [(-4.9,-1.9),(-2,0),(-2.4,1),(-3.2,1.6),(-4.7,1)]]

    # for i in range(args.seed_range,100):
        random.seed(args.seed)
        print("Generating Random Environment")
        no_obs = random.randint(8, 15)

        while True:
            obs=[]
            for i in range(no_obs):
                print("Object ",i)
                no_nbrs = random.randint(5, 8,) #(5,8)
                randm_int = random.randint(0, 99)

                x = [random.uniform(-5, 5) for x in range(100)]
                y = [random.uniform(-3, 3) for x in range(100)]


                coords = np.array(list(zip(x,y)))

                coords_ = sorted(coords, key=lambda point: euclidian_distance(point, coords[randm_int]))
                coords_= np.array(coords_)
                coords_ = coords_[:no_nbrs]
                coords_=list(map(tuple, coords_))

                points =np.array(coords_)
                hull = ConvexHull(points)

                # Merge intersecting objects
                ob_new = [points[x] for x in list(hull.vertices)]
                p_new = Polygon(ob_new)

                if args.merge:
                    obs_new = []
                    merged = False
                    for ob in obs:
                        p = Polygon(ob)
                        if (p_new.intersects(p)):
                            print('Merging objects')
                            p_union = unary_union((p_new,p))
                            ob_new = list(p_union.exterior.coords)
                            obs_new.append(ob_new)
                            merged = True
                        else:
                            print('Objects do not intersect')
                            obs_new.append(ob)
                    if not merged:
                        obs_new.append(ob_new)
                    obs = obs_new
                else:
                    obs.append([points[x] for x in list(hull.vertices)])


            check=[]
            for a, b in itertools.combinations(obs, 2):
                p1 = Polygon(a)
                p2 = Polygon(b)
                if (p1.intersects(p2)):
                    check.append('yes')
                else:
                    check.append('no')
            if len(set(check)) == 1 and check[0] == 'no':
                print(obs)
                break


        obstacles = []
        for ob in obs:
            obstacles.append(polyObstacle(ob))
        obs_boundaries = [obstacle.get_boundaries() for obstacle in obstacles]

    
    # Straight Edges
    cspace = [(-5, 5), (-3, 3)]
    qI = (-4.25, -2.5)
    qG = (4, -1)
    
    if args.env == 'complex_pro':
        while True:

            # print(2)
            list_a = []
            qI = (random.uniform(-5.0, 5.0), random.uniform(-3.0, 3.0))
            pointqI = Point(qI)
            for obstacle_ in obs_boundaries:
                polygonx = Polygon(obstacle_[:-1])

                if polygonx.contains(pointqI):
                    list_a.append(0)
                else:
                    list_a.append(1)
            if len(set(list_a)) == 1:
                break



        while True:
            # print(3)
            list_b = []
            qG = (random.uniform(-5.0, 5.0), random.uniform(-3.0, 3.0))
            pointqG = Point(qG)
            for obstacle_ in obs_boundaries:
                polygonx = Polygon(obstacle_[:-1])

                if polygonx.contains(pointqG):
                    list_b.append(0)
                else:
                    list_b.append(1)
            if len(set(list_b)) == 1:
                break

    #Reset random seed so that the sampled points are still random
    random.seed()

    world_boundary = WorldBoundary2D(cspace[0], cspace[1])
    obstacles.append(world_boundary)
    edge_creator = StraightEdgeCreator(0.1)
    collision_checker = ObstacleCollisionChecker(obstacles)
    distance_computator = EuclideanDistanceComputator()

    start_time = datetime.datetime.now()
    if args.alg == ALG_RRT:
        title = "RRT planning"
        (G, root, goal, iter_time) = rrt(
            cspace=cspace,
            qI=qI,
            qG=qG,
            edge_creator=edge_creator,
            distance_computator=distance_computator,
            collision_checker=collision_checker,
            numIt=args.numIt
        )
    elif args.alg == ALG_RRTstar:
        title = "RRT* planning"
        (G, root, goal, iter_time) = rrt_star(
            cspace=cspace,
            qI=qI,
            qG=qG,
            edge_creator=edge_creator,
            distance_computator=distance_computator,
            collision_checker=collision_checker,
            k=7, # 15,
            rho_min = rho_min,
            numIt=args.numIt,
            mode='straight'
        )
    elif args.alg == ALG_RRT_gpu:
        title = "RRT planning"
        (G, root, goal, iter_time) = rrt_gpu(
            cspace=cspace,
            qI=qI,
            qG=qG,
            edge_creator=edge_creator,
            distance_computator=EuclideanDistanceComputator(),
            collision_checker=collision_checker,
            numIt=args.numIt
        )
    elif args.alg == ALG_RRTstar_gpu:
        title = "RRT* planning"
        (G, root, goal, iter_time) = rrt_star_gpu(
            cspace=cspace,
            qI=qI,
            qG=qG,
            edge_creator=edge_creator,
            distance_computator=EuclideanDistanceComputator(),
            collision_checker=collision_checker,
            k=7, # 15,
            rho_min = rho_min,
            numIt=args.numIt,
            mode='straight'
        )

    path = []
    cost = 0
    if root is not None and goal is not None:
        path = G.get_path(root, goal)
        cost = G.get_cost(root, goal)
    if args.save=='do':
        file_name='data_'+args.alg+'_'+args.env+'_'+str(args.seed)+'_expN_'+str(args.exp)+'.xlsx'
        time_file = xlsxwriter.Workbook(file_name)
        time_file_sheet = time_file.add_worksheet() 
        time_file_sheet.write('A1', 'iteration_time')
        time_file_sheet.write('B1', 'total_time')
        time_file_sheet.write('C1', 'cost')   
        time_file_sheet.write('C2', cost)
    iteration_time = [(j-i).total_seconds()*1000 for i, j in zip(iter_time[:-1], iter_time[1:])]
    print(max(iteration_time))
    print(min(iteration_time))
    print(np.shape(iteration_time))
    plt.figure(figsize=(12, 9), dpi=300)
    plt.plot(iteration_time)
    plt.title('Time per Iteration')
    plt.xlabel('Iteration number')
    plt.ylabel('Time (ms)')
    plt.savefig('iter_plot.png')
    # plt.show()
    
    total_time = []
    for i in range(len(iteration_time)):
        total_time.append(np.sum(iteration_time[0:i])/1000)
        if args.save=='do':
            time_file_sheet.write('A'+str(i+2),iteration_time[i])
            time_file_sheet.write('B'+str(i+2),total_time[i])
    plt.figure(figsize=(12, 9), dpi=300)
    plt.plot(total_time)
    plt.title('Time vs Iteration')
    plt.xlabel('Iteration number')
    plt.ylabel('Time (seconds)')
    plt.savefig('time_plot.png')
    
    dt = datetime.datetime.now() - start_time
    print('time: ', dt)
    print('cost', cost)
    
    fig, ax = plt.subplots(1, 1)
    draw(ax, cspace, obs_boundaries, qI, qG, G, path, title)
    fig.set_size_inches(15, 9)
    plt_name='plt_'+args.alg+'_'+args.env+'_'+str(args.seed)+'_expN_'+str(args.exp)+'.png'
    plt.savefig(plt_name, dpi=300)
    # plt.show()
    
    # dt = datetime.datetime.now() - start_time
    # print('time: ', dt)
    # print('cost', cost)
    if args.save=='do':
        time_file.close()
