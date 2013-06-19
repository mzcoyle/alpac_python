#------------------------------------------------------------------------------
# Name:         fellerbuncher_silvi.py
# Purpose:      Establish harvest areas using feller buncher data
#
# Author:       Mathew Coyle
#
# Created:      29/03/2012
# Copyright:    (c) Alberta-Pacific 2012
# Licence:      ArcInfo
#------------------------------------------------------------------------------
#!/usr/bin/env python

# Import modules
import os
import sys
import datetime
import arcpy


def main(
        max_line=10,
        select_dist="12 Meters",
        buffer_dist="8 Meters",
        neg_buffer_dist="-3 Meters",
        min_area=1000,
        xytol="1 Meters"):

    """
    Main function to establish harvest areas of feller buncher.
    Requires feature class of blocks to analyze and feller buncher point data

    Standard parameters
    max_line = 10
    select_dist = "12 Meters"
    buffer_dist = "8 Meters"
    neg_buffer_dist = "-3 Meters"
    min_area = 1000
    xytol = "1 Meters"
    """
    #FB_ID = !SOURCEID! +"_"+ str(int( !Shape_Area!))

    # Import custom toolbox
    #arcpy.ImportToolbox(r"C:\GIS\tools\PointsToLines10\PointsToLines10.tbx")
    arcpy.ImportToolbox(r"\\millsite.net\filesystem\GISData\gis\tools\pointstolines10\PointsToLines10.tbx")

    # User variables
    max_line = 15  # maximum distance between points to join as connected path
    select_dist = "20 Meters"  # distance around block to assign points to it
    buffer_dist = "4 Meters"  # distance to buffer path
    neg_buffer_dist = "-1 Meters"  # distance to shrink from edges
    min_area = 100  # minimum area of holes to allow inside block
    xytol = "0.5 Meters"  # environment tolerance
    outName = "FINAL_HARVEST_US"

    # Set input data
    source_shp_dir = r"D:\GIS\FellerBuncher\testing\fb_data"
    output = r"D:\GIS\FellerBuncher\testing\testing.gdb"  # output GDB
    scratch = r"C:\temp\scratch_fb.gdb"  # Scratch GDB only need folder
    inFeatures = "block1"  # blocks FC requires SOURCEID field

    # Set local variables
    fblayer = r"in_memory\fbtemplayer"
    lineField = ""
    sortField = "TIMETAG"
    sourceField = "SOURCEID"
    fbidField = "FB_ID"
    fb_fc = "fb_points_merged"
    fbidcode = "FB_CODE_ID"
    block_layer = r"in_memory\blocktemp"
    out_data = r"in_memory\output"
    temp_lyr = r"in_memory\temp"
    b = None
    upcur = None
    row = None

    # Environment settings
    if not arcpy.Exists(output):
        print("Source database not found")
    scratch = scratch_creation(scratch)
    print("Preparing data")
    arcpy.env.workspace = source_shp_dir  # input
    arcpy.env.scratchWorkspace = scratch
    arcpy.env.overwriteOutput = True
    arcpy.env.XYTolerance = xytol

    # Create list of input shapefiles
    fc_in_list = []
    shape_source_list = arcpy.ListFeatureClasses("*.shp", "Point")
    fb_field_status = "Status"
    fb_status = "WRK"

    fb_field_delim = arcpy.AddFieldDelimiters(
        shape_source_list[0], fb_field_status)

    for in_shape in shape_source_list:
        fb_base = in_shape.split(".")[0]
        out_temp_path = os.path.join(output, fb_base)
        if not arcpy.Exists(out_temp_path):

            arcpy.FeatureClassToFeatureClass_conversion(
                in_features=in_shape,
                out_path=output,
                out_name=fb_base,
                where_clause="{0} = '{1}'".format(fb_field_delim, fb_status))

            fc_in_list.append(fb_base)
        if fbidcode not in arcpy.ListFields(out_temp_path, fbidcode)[0]:
            arcpy.AddField_management(
                in_table=out_temp_path,
                field_name=fbidcode,
                field_type="TEXT",
                field_length="15")

        upcur = arcpy.UpdateCursor(out_temp_path)
        for row in upcur:
            row.setValue(fbidcode, fb_base)
            upcur.updateRow(row)

    # Merge new input files

    arcpy.env.workspace = output
    if not arcpy.Exists(fb_fc):
        print('Merging points')
        arcpy.Merge_management(fc_in_list, fb_fc)
    else:
        print(
            'Merged feller buncher dataset already exists, '
            'choose option...' + os.linesep)

        code = raw_input(
            '1:     If you wish to keep the current merged dataset{0}'
            '2:     If you wish to rebuild the input{0}'
            '3:     If you would like to exit this script{0}'
            'Enter Choice: '.format(os.linesep))

        if code in ['1', '2', '3']:
            if code == '1':
                pass
            elif code == '2':
                arcpy.Merge_management(fc_in_list, fb_fc)
            elif code == '3':
                sys.exit()

        else:
            print('Invalid code, exiting application')
            sys.exit()

    # Check for FB_ID field in block layer, add and calculate if not found

    if not [f.name for f in arcpy.ListFields(inFeatures, fbidField)]:
        arcpy.AddField_management(
            in_table=inFeatures,
            field_name=fbidField,
            field_type="TEXT",
            field_length="25")

        exp = "!SOURCEID!+'_'+str(int(!Shape_Area!))"
        arcpy.CalculateField_management(
            in_table=inFeatures,
            field=fbidField,
            expression=exp,
            expression_type="PYTHON_9.3")

    # Build cursor to get list of blocks then delete cursor
    blocks_list = [
        row[0] for row in arcpy.da.SearchCursor(
        in_table=inFeatures,
        field_names=fbidField)]

    # Build index of feller bunchers
    FBindex = list()

    [
        FBindex.append(row.getValue(fbidcode))
        for row in arcpy.SearchCursor(
            fb_fc, "", "", fbidcode, "{0} A".format(fbidcode))
        if row.getValue(fbidcode) not in FBindex]

    '''IDval = row.getValue(fbidcode)
    if IDval not in FBindex:
        FBindex.append(IDval)'''

    # Loop through block list
    for b in blocks_list:
        print("\nProcessing {0}".format(b))
        where = "{0} = '{1}'".format(fbidField, b)
        arcpy.MakeFeatureLayer_management(
            in_features=inFeatures,
            out_layer=block_layer,
            where_clause=where)

        for feller in FBindex:
            print(feller)
            # can add in_memory when running output for perm
            b_path = os.path.join(
                scratch, "{0}{1}".format(b, feller))

            arcpy.MakeFeatureLayer_management(
                in_features=fb_fc,
                out_layer=fblayer,
                where_clause="{0} = '{1}'".format(fbidcode, feller))

            arcpy.SelectLayerByLocation_management(
                in_layer=fblayer,
                overlap_type="WITHIN_A_DISTANCE",
                select_features=block_layer,
                search_distance=select_dist,
                selection_type="NEW_SELECTION")

            selection = int(arcpy.GetCount_management(fblayer).getOutput(0))
            if selection != 0:
                print("{0} points for {1}".format(selection, feller))

                # Execute PointsToLine

                #arcpy.PointsToLine_management(
                    #fblayer, out_data, lineField, sortField)
                """
                Uncomment the previous line and comment out the next line if
                not using custom Points to Line tool.  This means the output
                may have errors from not using the max_line input.
                """

                arcpy.PointsToLinev10(
                    Input_Features=fblayer,
                    Output_Feature_Class=out_data,
                    Line_Field=lineField,
                    Sort_Field=sortField,
                    Max_Line_Length=max_line)

                arcpy.MakeFeatureLayer_management(out_data, temp_lyr)

                arcpy.SelectLayerByLocation_management(
                    in_layer=temp_lyr,
                    overlap_type="INTERSECT",
                    select_features=block_layer,
                    selection_type="NEW_SELECTION")

                arcpy.Buffer_analysis(
                    in_features=temp_lyr,
                    out_feature_class="{0}_buffer".format(b_path),
                    buffer_distance_or_field=buffer_dist,
                    line_side="FULL",
                    line_end_type="ROUND",
                    dissolve_option="ALL")

                # Double repair to ensure no errors
                arcpy.RepairGeometry_management(
                    "{0}_buffer".format(b_path),
                    "DELETE_NULL")

                arcpy.RepairGeometry_management(
                    "{0}_buffer".format(b_path),
                    "DELETE_NULL")

                # Eliminates holes below minimum area
                arcpy.EliminatePolygonPart_management(
                    in_features="{0}_buffer".format(b_path),
                    out_feature_class="{0}_eliminate".format(b_path),
                    condition="AREA",
                    part_area=min_area,
                    part_option="CONTAINED_ONLY")

                arcpy.RepairGeometry_management(
                    "{0}_eliminate".format(b_path),
                    "DELETE_NULL")

                # Add base SOURCEID field without unique area identifier
                arcpy.AddField_management(
                    in_table="{0}_eliminate".format(b_path),
                    field_name=sourceField,
                    field_type="TEXT",
                    field_length="25")

                # Add SOURCEID to output feature
                upcur = arcpy.UpdateCursor("{0}_eliminate".format(b_path))
                for row in upcur:
                    row.setValue(sourceField, b.split("_")[0])
                    upcur.updateRow(row)
                del upcur

        #for feller in FBindex: Loop ended
    #for b in blocks_list: Loop ended

    print("\nProcessing final block areas")
    # Path to final output feature class
    final_output = os.path.join(output, outName)
    arcpy.env.workspace = scratch
    fcs_final = arcpy.ListFeatureClasses("*_eliminate")
    arcpy.Merge_management(
        inputs=fcs_final,
        output="final_harvest_merge")

    # Union blocks together to create features from overlap
    arcpy.Union_analysis(
        in_features="final_harvest_merge",
        out_feature_class="final_harvest_union",
        join_attributes="NO_FID",
        cluster_tolerance=xytol,
        gaps="GAPS")

    # Dissolve unioned fc based on source field
    arcpy.Dissolve_management(
        in_features="final_harvest_union",
        out_feature_class="final_harvest_dissolve",
        dissolve_field=sourceField,
        multi_part="SINGLE_PART")

    # Eliminate doughnut holes below minimum area criterion
    arcpy.EliminatePolygonPart_management(
        in_features="final_harvest_dissolve",
        out_feature_class="final_harvest_elim",
        condition="AREA",
        part_area=min_area,
        part_option="CONTAINED_ONLY")

    # Negative buffer to compensate for ribbon line proximity
    if neg_buffer_dist != "0 Meters":
        arcpy.Buffer_analysis(
            in_features="final_harvest_elim",
            out_feature_class=final_output,
            buffer_distance_or_field=neg_buffer_dist,
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="LIST",
            dissolve_field=sourceField)

    # If no negative buffer simply export the eliminate output
    else:
        arcpy.FeatureClassToFeatureClass_conversion(
            in_features="final_harvest_elim",
            out_path=output,
            out_name=outName)

    arcpy.RepairGeometry_management(
        final_output,
        "DELETE_NULL")


def scratch_creation(scratch):
    """scratcb_creation(scratch)

    Create scratch geodatabase

    scratch(string)
    Path to geodatabase root"""

    scratch_create = True
    for i in range(0, 10):
        if scratch_create:
            scratch_return = "{0}{1}.gdb".format(
                scratch.split(".gdb")[0], i)

            if not arcpy.Exists(scratch_return):
                arcpy.CreateFileGDB_management(
                    os.path.dirname(scratch_return),
                    os.path.basename(scratch_return))

                print("Creating {0}".format(scratch_return))
                scratch_create = False
            else:
                print("Deleting {0}".format(scratch_return))
                arcpy.Delete_management(scratch_return)
    return scratch_return

if __name__ == "__main__":

    start_time = datetime.datetime.now()

    print("Start time {0}".format(start_time))

    # Call main function
    main()

    print("Elapsed time {0}".format(datetime.datetime.now() - start_time))
